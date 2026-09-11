"""Bengali + English narrative around the portfolio plan.

Gemini writes the explanation when a key is available; otherwise an honest
template narrates the exact same numbers. In every mode the text is
educational, never a return promise.
"""
import json

from portfolio.intent import QUICK_MODEL

BENGALI_T = 'বাংলা'
_LANG_HINT = (
    "Write exactly three sections in this order:\n"
    "1. **বাংলা সারসংক্ষেপ** — 4-6 sentences in Bengali explaining the plan.\n"
    "2. **English summary** — 4-6 sentences.\n"
    "3. **Risk bullets** — 3 bullets: fees/tax reality (equity STCG 20%, crypto"
    " gains 30% + TDS), stop-loss discipline, and that short-term trading is"
    " speculative with NO guaranteed returns.\n"
    "You are an educational explainer, NOT a licensed advisor. Never promise,"
    " guarantee or predict returns. Use only the numbers in the JSON facts."
)


def _facts(spec, plans, backtests):
    """Compact JSON of everything real in the plan — the LLM may only use this."""
    out = {'goal': {k: spec[k] for k in ('amount_inr', 'markets', 'horizon', 'risk')},
           'markets': {}}
    for market, plan in (plans or {}).items():
        bt = backtests.get(market) or {}
        out['markets'][market] = {
            'invested_inr': plan.get('invested'),
            'cash_left_inr': plan.get('cash_left'),
            'positions': [
                {k: p[k] for k in ('ticker', 'name', 'weight', 'alloc_inr', 'qty',
                                   'entry', 'stop', 'target', 'net_at_target',
                                   'net_at_stop')}
                for p in plan.get('positions', [])
            ],
            'walk_forward_6mo': {
                'strategy_total_pct': None if bt.get('total') is None else round(bt['total'] * 100, 1),
                'benchmark_total_pct': None if bt.get('bench_total') is None else round(bt['bench_total'] * 100, 1),
                'max_drawdown_pct': None if bt.get('max_dd') is None else round(bt['max_dd'] * 100, 1),
                'n_rebalances': bt.get('n_rebalances'),
            },
        }
    return json.dumps(out, ensure_ascii=False, default=str)


def narrate_plan(spec_dict, plans, backtests, api_key=None):
    """spec_dict may be a GoalSpec or its dict; returns markdown text."""
    spec = spec_dict.to_dict() if hasattr(spec_dict, 'to_dict') else dict(spec_dict)
    facts = _facts(spec, plans, backtests)

    if api_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            model = ChatGoogleGenerativeAI(model=QUICK_MODEL, google_api_key=api_key,
                                           temperature=0.2, max_tokens=900)
            response = model.invoke([
                ('system', _LANG_HINT),
                ('human', 'Facts JSON:\n' + facts),
            ])
            text = getattr(response, 'content', None) or ''
            if len(text.strip()) > 80:
                return text.strip()
        except Exception:
            pass
    return _template(spec, plans, backtests)


def _money(value):
    return '₹{:,.0f}'.format(float(value or 0))


def _template(spec, plans, backtests):
    """Same honesty as the LLM path, generated from the actual numbers."""
    amount = spec.get('amount_inr', 0)
    horizon = spec.get('horizon', 'short')
    risk = spec.get('risk', 'medium')
    lines = ['## বাংলা সারসংক্ষেপ', '']
    lines.append('{} টাকার জন্য {} horizon ও {} risk profile অনুযায়ী একটা '
                 'cost-aware পোর্টফোলিও প্ল্যান বানানো হয়েছে। প্রতিটা পিকে '
                 'momentum, volatility ও liquidity-র উপর ভিত্তি করে নেওয়া, '
                 'ওজন volatility-র বিপরীতমুখী, আর প্রতিটার সাথে ATR-ভিত্তিক '
                 'stop-loss ও 2R target দেওয়া আছে। ফি, STT এবং আনুমানিক কর '
                 '(ইকুইটি STCG 20%, ক্রিপ্টো 30%) সব হিসাবে ধরা।'.format(
                     _money(amount), horizon, risk))
    lines.append('')
    for market, plan in (plans or {}).items():
        wf = (backtests.get(market) or {})
        pos = plan.get('positions', [])
        names = ', '.join(p['ticker'] for p in pos) or 'কোনো সামর্থ্যযোগ্য পিক নেই'
        wf_line = ''
        if wf.get('total') is not None:
            wf_line = ' গত ৬ মাসের walk-forward: এই স্ক্রিন {:.1f}% বনাম benchmark {:.1f}%.'.format(
                wf['total'] * 100,
                (wf['bench_total'] or 0.0) * 100)
        lines.append('- **{}**: {}{} বাকি নগদ {}.'.format(
            market, names, wf_line, _money(plan.get('cash_left'))))
    lines += ['', '## English summary', '',
              'This plan allocates {} across the markets you asked for, using a '
              'deterministic momentum screen (no LLM picks the assets). Weights are '
              'inverse-volatility with per-pick caps, stocks are sized in whole '
              'shares you can actually afford, and every position carries an ATR '
              'stop and a 2R target. All figures for fees, STT and estimated tax '
              'are already netted out.'.format(_money(amount))]
    lines += ['', '## Risk bullets', '',
              '- **Fees & tax are real:** equity short-term gains are taxed at 20%, '
              'crypto gains at 30% (+1% TDS on sells) — small, frequent trades get '
              'eaten alive by costs.',
              '- **Stops are discipline, not decoration:** if price hits the stop, '
              'the plan says exit; averaging down on a broken thesis is how small '
              'accounts become smaller.',
              '- **No guarantees:** short-term trading is speculative. The '
              'walk-forward backtest validates the screen historically — past '
              'performance does not predict future results.']
    return '\n'.join(lines)

