"""Streamlit page for the goal-based portfolio mode ('🎯 Goal portfolio').

Called from app.py's sidebar mode switch; the single-stock analysis flow
never runs in this mode, so the two features stay fully independent.
"""
import json

import pandas as pd
import streamlit as st

from goaldesk import allocate as al
from goaldesk import backtest as bt
from goaldesk import intent as it
from goaldesk import narrate as nr
from goaldesk import screener as sc
from goaldesk.data import fetch_fx_usdinr, fetch_history
from goaldesk.universe import BENCHMARKS, BENCHMARK_LABELS, MARKET_LABELS, UNIVERSES

EXAMPLE_GOALS = [
    'আমি ₹20,000 ইন্ডিয়ান মার্কেট বা ক্রিপ্টো মার্কেটে invest করতে চাই — শর্ট '
    'পিরিয়ডে ভালো return দেবে এমন stock/coin দাও',
    'I want to invest 20000 rupees in the Indian market or crypto market. '
    'Get me some good-return stocks or coins in a short period of time',
    '50k in stocks only, medium risk',
    '₹30,000 crypto aggressive quick',
]


def _secrets_get(key):
    """st.secrets.get that survives a missing secrets.toml (local runs)."""
    try:
        return st.secrets.get(key)
    except Exception:
        return None


@st.cache_data(ttl=900, show_spinner=False)
def _cached_history(tickers_tuple):
    return fetch_history(list(tickers_tuple))


def _split_budget(markets, risk):
    """Budget fraction per requested market."""
    if len(markets) == 1:
        return {markets[0]: 1.0}
    india, crypto = al.RISK_SPLIT.get(risk, (0.60, 0.40))
    return {'india': india, 'crypto': crypto}


def _run_pipeline(spec):
    """Intent → data → screen → allocate → backtest → narrative bundle."""
    google_key = _secrets_get('GOOGLE_API_KEY')
    markets = spec.markets
    universe_tickers = [t for m in markets for t in UNIVERSES[m]]
    bench_tickers = [BENCHMARKS[m] for m in markets]
    frames = _cached_history(tuple(universe_tickers + bench_tickers))
    fx = fetch_fx_usdinr()
    if not frames:
        raise RuntimeError('Yahoo Finance থেকে কোনো ডেটা পাওয়া যায়নি / no market data returned')

    fractions = _split_budget(markets, spec.risk)
    plans, backtests, scored = {}, {}, {}
    for market in markets:
        rows = []
        for ticker, df in frames.items():
            if ticker in UNIVERSES[market]:
                metrics = sc.compute_metrics(df, market)
                if metrics:
                    metrics['ticker'] = ticker
                    metrics['name'] = UNIVERSES[market][ticker]
                    rows.append(metrics)
        table = sc.score_universe(rows, spec.horizon)
        scored[market] = table
        picks = sc.shortlist(table, spec.risk, spec.top_n)
        amount = spec.amount_inr * fractions.get(market, 1.0)
        plans[market] = al.build_portfolio(picks, amount, spec.risk, market, fx)

        close_cols = {t: f['Close'] for t, f in frames.items()
                      if t in UNIVERSES[market] or t == BENCHMARKS[market]}
        closes = pd.DataFrame(close_cols)
        backtests[market] = bt.walk_forward(
            closes, market,
            risk_max_vol=sc.RISK_MAX_VOL[spec.risk],
            k=max(len(picks), 3) if picks else 5,
            benchmark=BENCHMARKS[market])

    story = nr.narrate_plan(spec.to_dict(), plans, backtests, google_key)
    return {'spec': spec.to_dict(), 'fx': fx, 'plans': plans,
            'backtests': backtests, 'scored': scored, 'story': story}


def _goal_form():
    st.markdown('<div class="section-label">01 · আপনার লক্ষ্য (your goal)</div>',
                unsafe_allow_html=True)
    goal = st.text_area('স্বপ্নটা সাধারণ ভাষায় লিখুন · describe your goal in plain language',
                        value=EXAMPLE_GOALS[0], height=96, key='goal_text')
    chips = st.columns(len(EXAMPLE_GOALS))
    for idx, col in enumerate(chips):
        with col:
            if st.button(f'📝 উদাহরণ {idx + 1}', key=f'example_{idx}',
                         use_container_width=True):
                st.session_state['goal_text'] = EXAMPLE_GOALS[idx]
                st.rerun()

    with st.expander('⚙️ Manual override (চাইলে নিজে ঠিক করুন)'):
        manual = st.checkbox('Use manual settings', key='manual_override')
        c1, c2 = st.columns(2)
        with c1:
            amount = st.number_input('Amount (₹)', min_value=1000, max_value=10_000_000,
                                     value=20000, step=1000, key='manual_amount')
            risk = st.radio('Risk', ('low', 'medium', 'high'), index=1,
                            horizontal=True, key='manual_risk')
        with c2:
            markets = st.multiselect('Markets', ('india', 'crypto'),
                                     default=('india', 'crypto'), key='manual_markets')
            horizon = st.radio('Horizon', ('short', 'medium', 'long'), index=0,
                               horizontal=True, key='manual_horizon')
    return goal, manual, amount, markets, risk, horizon


def _position_table(plan):
    rows = []
    for p in plan['positions']:
        rows.append({
            'Ticker': p['ticker'],
            'Name': p['name'],
            'Weight %': round(p['weight'] * 100, 1),
            'Allocation ₹': p['alloc_inr'],
            'Qty': p['qty'],
            'Entry ₹': p['entry'],
            'Stop ₹': p['stop'],
            'Target ₹': p['target'],
            'Net @ target ₹': p['net_at_target'],
            'Net @ stop ₹': p['net_at_stop'],
            'RSI': p['rsi14'],
            'Vol (ann.)': p['vol_ann'],
        })
    return pd.DataFrame(rows)


def _plan_csv(bundle):
    lines = ['market,ticker,name,weight_pct,alloc_inr,qty,entry_inr,stop_inr,target_inr,net_at_target,net_at_stop,rsi14']
    for market, plan in bundle['plans'].items():
        for p in plan['positions']:
            lines.append('{},{},{},{},{},{},{},{},{},{},{},{}'.format(
                market, p['ticker'], p['name'].replace(',', ' '),
                round(p['weight'] * 100, 2), p['alloc_inr'], p['qty'], p['entry'],
                p['stop'], p['target'], p['net_at_target'], p['net_at_stop'], p['rsi14']))
    return '\n'.join(lines)


def render_portfolio_page():
    st.markdown('''
    <div class="hero">
        <div class="eyebrow">SANJIB'S MARKET INTELLIGENCE · GOAL DESK (BETA)</div>
        <div class="hero-title">একটা বাক্য লিখুন — পুরো প্ল্যান পান।</div>
        <div class="hero-copy">A deterministic momentum screen (never an LLM) picks the assets; Gemini only explains the plan. Every pick ships with an ATR stop, a 2R target, and fees + tax already netted out.</div>
        <div class="status-row">
            <span class="status-pill"><span class="dot"></span> Screener online</span>
            <span class="status-pill">◈ Walk-forward validated</span>
            <span class="status-pill">⚠ Educational — not investment advice</span>
        </div>
    </div>
    ''', unsafe_allow_html=True)

    goal, manual, amount, markets, risk, horizon = _goal_form()

    if st.button('🚀 পোর্টফোলিও প্ল্যান বানাও · Build my portfolio plan',
                 type='primary', use_container_width=True, key='build_plan'):
        st.session_state['portfolio_bundle'] = None
        with st.status('Pipeline চলছে · data → screen → allocate → backtest',
                       expanded=True) as status:
            st.write('১/৪ · লক্ষ্য বোঝা হচ্ছে (Gemini, fallback: rules)…')
            spec = it.parse_intent(goal, _secrets_get('GOOGLE_API_KEY'))
            if manual:
                spec.amount_inr = float(amount)
                spec.markets = markets or ['india']
                spec.risk = risk
                spec.horizon = horizon
                spec.source = 'manual'
            st.write('২/৪ · ডেটা আনা হচ্ছে (yfinance)…')
            try:
                bundle = _run_pipeline(spec)
            except Exception as exc:
                st.session_state['portfolio_bundle'] = None
                st.session_state['portfolio_error'] = str(exc)
                status.update(label='Pipeline failed', state='error')
            else:
                st.session_state['portfolio_bundle'] = bundle
                st.session_state.pop('portfolio_error', None)
                status.update(label='প্ল্যান রেডি!', state='complete')

    if st.session_state.get('portfolio_error'):
        st.error('Pipeline ব্যর্থ: ' + st.session_state['portfolio_error'])

    bundle = st.session_state.get('portfolio_bundle')
    if not bundle:
        return

    spec, plans, backtests = bundle['spec'], bundle['plans'], bundle['backtests']
    st.markdown('<div class="section-label">02 · প্ল্যান (the plan)</div>',
                unsafe_allow_html=True)
    chips = ' · '.join([
        '🎯 ₹{:,.0f}'.format(spec['amount_inr']),
        '🌐 ' + ' + '.join(spec['markets']),
        '⏱ ' + spec['horizon'],
        '🎚 risk: ' + spec['risk'],
        '🤖 intent: ' + spec['source'],
        '💱 USD/INR {:.2f}'.format(bundle['fx']),
    ])
    st.markdown('<div class="status-row"><span class="status-pill">{}</span></div>'
                .format(chips), unsafe_allow_html=True)

    total_invested = sum(p['invested'] for p in plans.values())
    total_cash = sum(p['cash_left'] for p in plans.values())
    net_target = sum(p['net_at_target'] for plan in plans.values()
                     for p in plan['positions'])
    net_stop = sum(p['net_at_stop'] for plan in plans.values()
                   for p in plan['positions'])
    m1, m2, m3, m4 = st.columns(4)
    m1.metric('Invested', '₹{:,.0f}'.format(total_invested),
              'cash ₹{:,.0f}'.format(total_cash))
    m2.metric('Net if all targets hit', '+₹{:,.0f}'.format(net_target))
    m3.metric('Net if all stops hit', '₹{:,.0f}'.format(net_stop))
    m4.metric('Positions', str(sum(len(p['positions']) for p in plans.values())))

    for market, plan in plans.items():
        st.subheader('{} · {}'.format(MARKET_LABELS.get(market, market),
                                      BENCHMARK_LABELS.get(market, '')))
        table = _position_table(plan)
        if table.empty:
            st.warning('এই বাজেটে এই মার্কেটে কেনার মতো কিছু পাওয়া যায়নি — '
                       'amount বাড়িয়ে দেখুন।')
        else:
            st.dataframe(table, use_container_width=True, hide_index=True)
        btres = backtests.get(market)
        if btres:
            chart = pd.DataFrame({'strategy': btres['curve']})
            if btres['bench_curve'] is not None:
                chart['benchmark'] = btres['bench_curve']
            st.line_chart(chart, height=220)
            st.caption('Walk-forward (৬ মাস, ১৪ দিন পরপর রিব্যালেন্স, খরচ বাদিয়ে): '
                       'strategy **{:.1%}** vs benchmark **{:.1%}** · max DD {:.1%} · '
                       'win rate {} · {} rebalances'.format(
                           btres['total'],
                           btres['bench_total'] if btres['bench_total'] is not None else 0.0,
                           btres['max_dd'], btres['win_rate'], btres['n_rebalances']))

    st.markdown('#### 🧠 প্ল্যানের ব্যাখ্যা (বাংলা + English)')
    st.markdown(bundle['story'])

    with st.expander('💸 Costs, tax & honest fine print'):
        st.markdown(
            '- স্টক: brokerage ₹20/side + STT 0.1% (sell) + misc ≈ 0.25% round trip\n'
            '- ক্রিপ্টো (ভারতীয় এক্সচেঞ্জ): ~0.25%/side ফি + spread\n'
            '- ইকুইটি short-term gain কর **20%**, ক্রিপ্টো gain কর **30%** (+1% TDS)\n'
            '- Yahoo-র crypto দাম USD — INR সাইজিং লাইভ USD/INR দিয়ে; ভারতীয় এক্সচেঞ্জে '
            'প্রিমিয়াম/ডিসকাউন্ট থাকতে পারে\n'
            '- এই টুল **শিক্ষামূলক**; SEBI-রেজিস্টার্ড advice নয়; returns-এর কোনো গ্যারান্টি নেই')

    dl1, dl2 = st.columns(2)
    dl1.download_button('⬇ Download plan (.csv)', _plan_csv(bundle).encode('utf-8'),
                        file_name='goal_portfolio_plan.csv', mime='text/csv',
                        use_container_width=True)
    dl2.download_button('⬇ Download plan (.json)',
                        json.dumps({'spec': spec, 'plans': plans, 'fx': bundle['fx']},
                                   ensure_ascii=False, default=str).encode('utf-8'),
                        file_name='goal_portfolio_plan.json',
                        mime='application/json', use_container_width=True)

    st.warning('⚠️ **Disclaimer:** এটা একটা educational decision-support টুল — '
               'বিনিয়োগ advice নয়। মার্কেট ঝুঁকিপূর্ণ; short-term trading-এ '
               'মূলধন পুরোপুরি হারানোর ঝুঁকি আছে। বিনিয়োগের আগে SEBI-রেজিস্টার্ড '
               'উপদেষ্টার সাথে কথা বলুন।', icon='⚠️')



