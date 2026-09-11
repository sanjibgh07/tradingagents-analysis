import streamlit as st
import yfinance as yf
import os
import time
import html
from datetime import date, timedelta
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

st.set_page_config(
    page_title='Sanjib Market Intelligence',
    page_icon='📈',
    layout='wide',
    initial_sidebar_state='collapsed',
)

st.markdown('''
<style>
    .stApp {
        background: radial-gradient(circle at 8% 0%, rgba(88, 101, 242, 0.12), transparent 28%),
                    radial-gradient(circle at 92% 8%, rgba(0, 200, 170, 0.10), transparent 25%);
    }
    .block-container { max-width: 1320px; padding-top: 2rem; padding-bottom: 4rem; }
    .hero {
        padding: 1.6rem 1.8rem 1.7rem;
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 1.25rem;
        background: linear-gradient(135deg, rgba(30,34,48,0.96), rgba(20,24,36,0.88));
        box-shadow: 0 18px 55px rgba(0,0,0,0.22);
        margin-bottom: 1.25rem;
    }
    .eyebrow { font-size: 0.78rem; letter-spacing: 0.14em; text-transform: uppercase; opacity: 0.62; font-weight: 700; }
    .hero-title { font-size: clamp(2rem, 4vw, 3.25rem); line-height: 1.05; font-weight: 800; margin: 0.35rem 0 0.6rem; }
    .hero-copy { font-size: 1rem; opacity: 0.72; max-width: 760px; line-height: 1.6; }
    .status-row { display:flex; gap:0.55rem; flex-wrap:wrap; margin-top:1rem; }
    .status-pill { display:inline-flex; align-items:center; gap:0.4rem; padding:0.42rem 0.7rem; border-radius:999px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.08); font-size:0.78rem; }
    .dot { width:7px; height:7px; border-radius:50%; background:#35d39a; display:inline-block; box-shadow:0 0 10px rgba(53,211,154,0.65); }
    .section-label { font-size:0.78rem; text-transform:uppercase; letter-spacing:0.12em; font-weight:750; opacity:0.55; margin:0.25rem 0 0.65rem; }
    .decision-card { padding:1.25rem 1.4rem; border-radius:1rem; border:1px solid rgba(255,255,255,0.10); background:rgba(255,255,255,0.035); margin:0.8rem 0 1.25rem; }
    .decision-caption { font-size:0.78rem; text-transform:uppercase; letter-spacing:0.12em; opacity:0.55; font-weight:700; }
    .decision-value { font-size:2.4rem; font-weight:850; margin-top:0.2rem; }
    .decision-meta { opacity:0.58; font-size:0.86rem; margin-top:0.15rem; }
    div[data-testid="stVerticalBlockBorderWrapper"] { border-radius:1rem; }
    div.stButton > button { border-radius:0.7rem; min-height:2.7rem; font-weight:750; transition:all .18s ease; }
    div.stButton > button:hover { transform:translateY(-1px); }
    [data-testid="stTextInputRootElement"] input, [data-testid="stDateInputField"] { border-radius:0.7rem; }
    .footer { text-align:center; opacity:0.42; font-size:0.75rem; padding-top:1.5rem; }
</style>
''', unsafe_allow_html=True)

if not st.session_state.get('auth'):
    st.markdown('''
    <div class="hero">
        <div class="eyebrow">SANJIB'S MARKET INTELLIGENCE</div>
        <div class="hero-title">Think clearly. Trade deliberately.</div>
        <div class="hero-copy">A focused multi-agent research desk combining market data, sentiment, news, fundamentals, debate, risk and trader planning into one decision workflow.</div>
        <div class="status-row">
            <span class="status-pill"><span class="dot"></span> Analysis engine online</span>
            <span class="status-pill">✦ Gemini multi-agent</span>
            <span class="status-pill">◈ Checkpoint enabled</span>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    with st.container(border=True):
        st.subheader('Welcome back')
        st.caption('Sign in to open your private analysis desk.')
        user = st.text_input('Username')
        pw = st.text_input('Password', type='password')
        if st.button('Enter Analysis Desk', type='primary', use_container_width=True):
            if user == st.secrets['APP_USERNAME'] and pw == st.secrets['APP_PASSWORD']:
                st.session_state.auth = True
                st.rerun()
            else:
                st.error('Wrong username or password')
    st.markdown('<div class="footer">Sanjib Market Intelligence · Multi-agent decision support</div>', unsafe_allow_html=True)
    st.stop()

header_left, header_right = st.columns([6, 1])
with header_right:
    if st.button('↪ Logout', use_container_width=True):
        st.session_state.auth = False
        st.session_state.pop('analysis_running', None)
        st.session_state.pop('analysis_result', None)
        st.rerun()

st.markdown('''
<div class="hero">
    <div class="eyebrow">SANJIB'S MARKET INTELLIGENCE · LIVE DESK</div>
    <div class="hero-title">Your market. Eight perspectives. One decision.</div>
    <div class="hero-copy">Run a disciplined multi-agent analysis and inspect every layer of the reasoning—from raw market context to the final trade decision.</div>
    <div class="status-row">
        <span class="status-pill"><span class="dot"></span> Engine ready</span>
        <span class="status-pill">✦ Gemini</span>
        <span class="status-pill">◈ Checkpoint protected</span>
        <span class="status-pill">⌁ 8 intelligence modules</span>
    </div>
</div>
''', unsafe_allow_html=True)

st.markdown('<div class="section-label">01 · Analysis setup</div>', unsafe_allow_html=True)
with st.container(border=True):
    col1, col2, col3 = st.columns([2.2, 1.8, 1], vertical_alignment='bottom')
    with col1:
        ticker = st.text_input('Ticker symbol', 'AAPL', help='Enter a Yahoo Finance ticker such as AAPL, MSFT or NVDA.').upper().strip()
    with col2:
        d = st.date_input('Analysis date', date.today() - timedelta(days=1))
    with col3:
        analyze = st.button('⚡ Run Analysis', type='primary', use_container_width=True, disabled=st.session_state.get('analysis_running', False))

if analyze:
    if not ticker:
        st.error('Please enter a ticker symbol.')
        st.stop()

    st.session_state.analysis_running = True
    try:
        df = yf.download(ticker, period='3mo', progress=False, multi_level_index=False)
        if df is None or df.empty:
            st.error('No market data found for ' + ticker)
            st.stop()

        cfg = DEFAULT_CONFIG.copy()
        cfg['llm_provider'] = 'google'
        cfg['deep_think_llm'] = 'gemini-3.5-flash'
        cfg['quick_think_llm'] = 'gemini-3.1-flash-lite'
        cfg['google_thinking_level'] = 'minimal'
        cfg['temperature'] = 0
        cfg['max_tokens'] = 1500
        cfg['llm_max_retries'] = 2
        cfg['news_article_limit'] = 5
        cfg['global_news_article_limit'] = 3
        cfg['max_debate_rounds'] = 1
        cfg['max_risk_discuss_rounds'] = 1
        cfg['checkpoint_enabled'] = True
        os.environ['GOOGLE_API_KEY'] = st.secrets['GOOGLE_API_KEY']

        tg = TradingAgentsGraph(debug=False, config=cfg)
        max_attempts = 10
        for attempt in range(1, max_attempts + 1):
            try:
                with st.status(f'Agents working · pass {attempt}/{max_attempts}', expanded=True) as s:
                    final_state, decision = tg.propagate(ticker, d.strftime('%Y-%m-%d'))
                    s.update(label='Analysis complete', state='complete')
                break
            except Exception as e:
                msg = str(e)
                if attempt < max_attempts and ('429' in msg or 'rate limit' in msg.lower()):
                    st.warning(f'Rate limit encountered. Waiting 65 s, then resuming from the last checkpoint (pass {attempt + 1}/{max_attempts}). Keep this tab open.')
                    time.sleep(65)
                    continue
                raise

        st.session_state.analysis_result = {
            'ticker': ticker,
            'date': d.strftime('%d %b %Y'),
            'final_state': final_state,
            'decision': decision,
        }
    finally:
        st.session_state.analysis_running = False

result = st.session_state.get('analysis_result')
if result:
    final_state = result['final_state']
    decision = result['decision']
    ticker = result['ticker']
    analysis_date = result['date']

    dec = decision if isinstance(decision, str) else str(decision)
    safe_dec = html.escape(dec)
    dec_lower = dec.lower()
    if 'buy' in dec_lower:
        badge = '🟢'
    elif 'sell' in dec_lower:
        badge = '🔴'
    else:
        badge = '🟡'

    st.markdown('<div class="section-label">02 · Intelligence result</div>', unsafe_allow_html=True)
    st.markdown(f'''
    <div class="decision-card">
        <div class="decision-caption">Final portfolio signal</div>
        <div class="decision-value">{badge} {safe_dec}</div>
        <div class="decision-meta">{html.escape(ticker)} · analysis date {html.escape(analysis_date)} · generated by the multi-agent desk</div>
    </div>
    ''', unsafe_allow_html=True)

    # Desk brief — executive summary extracted from the final decision (UI-only string handling).
    fd_text = str(final_state.get('final_trade_decision', ''))
    fd_low = fd_text.lower()
    brief = ''
    if 'executive summary' in fd_low:
        seg = fd_text[fd_low.index('executive summary') + len('executive summary'):]
        seg = seg.lstrip(' :').strip()
        end = seg.lower().find('investment thesis')
        brief = (seg[:end] if end != -1 else seg[:600]).strip()
    if not brief:
        brief = fd_text[:600].strip()
    brief = brief.replace('**', '').replace('__', '').strip().strip('*').lstrip(':').strip()
    if brief:
        with st.container(border=True):
            st.caption('Desk brief — executive summary of the final decision')
            st.write(brief)


    reports = [
        ('Market', 'market_report', 'Price action, technical context and market regime.'),
        ('Sentiment', 'sentiment_report', 'Investor mood, positioning and sentiment signals.'),
        ('News', 'news_report', 'Recent company and market-moving news context.'),
        ('Fundamentals', 'fundamentals_report', 'Business quality, financials and valuation context.'),
        ('Bull / Bear Debate', 'investment_debate_state', 'Structured opposing-case investment debate.'),
        ('Risk Judge', 'risk_debate_state', 'Risk assessment and challenge to the proposed trade.'),
        ('Trader Plan', 'trader_investment_plan', 'Action plan derived from the research stack.'),
        ('Final Decision', 'final_trade_decision', 'The final synthesized trade decision.'),
    ]

    st.markdown('<div class="section-label">03 · Research stack</div>', unsafe_allow_html=True)
    expand_all = st.toggle('Expand all reports', key='expand_all_reports')
    left, right = st.columns(2, gap='large')
    for i, (title, key, description) in enumerate(reports):
        text = str(final_state.get(key, 'N/A'))
        words = len(text.split())
        target = left if i % 2 == 0 else right
        with target:
            with st.expander(f'{title} · {words:,} words', expanded=(expand_all or title == 'Final Decision')):
                st.caption(description)
                st.write(text)

    st.markdown('<div class="section-label">04 · Export</div>', unsafe_allow_html=True)
    report_lines = [
        'SANJIB MARKET INTELLIGENCE',
        f'Ticker: {ticker}',
        f'Analysis date: {analysis_date}',
        f'Final portfolio signal: {dec}',
        '',
    ]
    for title, key, description in reports:
        report_lines.extend([
            f'## {title}',
            description,
            '',
            str(final_state.get(key, 'N/A')),
            '',
        ])
    report_text = '\n'.join(report_lines)
    st.download_button(
        '⬇ Download complete report (.md)',
        data=report_text,
        file_name=f'{ticker}_{analysis_date.replace(" ", "_")}_market_intelligence.md',
        mime='text/markdown',
        use_container_width=True,
    )

    st.markdown('<div class="footer">Sanjib Market Intelligence · Gemini multi-agent research desk · Checkpoint protected</div>', unsafe_allow_html=True)
