import streamlit as st
import yfinance as yf
import os
import time
from datetime import date, timedelta
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

st.set_page_config(
    page_title='Trading Agents Analysis',
    page_icon='📈',
    layout='wide',
    initial_sidebar_state='collapsed',
)

st.markdown('''
<style>
    .block-container { padding-top: 2rem; padding-bottom: 3rem; }
    [data-testid="stMetric"] { padding: 0.75rem 1rem; border-radius: 0.75rem; }
    div.stButton > button { border-radius: 0.6rem; font-weight: 600; }
    .app-subtitle { opacity: 0.72; margin-top: -0.6rem; margin-bottom: 1.5rem; }
</style>
''', unsafe_allow_html=True)

if not st.session_state.get('auth'):
    st.title('📈 Trading Agents Analysis')
    st.markdown('<div class="app-subtitle">Multi-agent market analysis dashboard</div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.subheader('Sign in')
        user = st.text_input('Username')
        pw = st.text_input('Password', type='password')
        if st.button('Login', type='primary', use_container_width=True):
            if user == st.secrets['APP_USERNAME'] and pw == st.secrets['APP_PASSWORD']:
                st.session_state.auth = True
                st.rerun()
            else:
                st.error('Wrong username or password')
    st.stop()

st.title('📈 Trading Agents Analysis')
st.markdown('<div class="app-subtitle">Multi-agent market analysis dashboard</div>', unsafe_allow_html=True)

with st.container(border=True):
    st.subheader('Analysis setup')
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        ticker = st.text_input('Ticker', 'AAPL').upper()
    with col2:
        d = st.date_input('Analysis date', date.today() - timedelta(days=1))
    with col3:
        st.write('')
        st.write('')
        analyze = st.button('Analyze', type='primary', use_container_width=True)

if analyze:
    df = yf.download(ticker, period='3mo', progress=False, multi_level_index=False)
    if df is None or df.empty:
        st.error('No data for ' + ticker)
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
            with st.status(f'Agents working (attempt {attempt}/{max_attempts})...', expanded=True) as s:
                final_state, decision = tg.propagate(ticker, d.strftime('%Y-%m-%d'))
                s.update(label='Analysis complete', state='complete')
            break
        except Exception as e:
            msg = str(e)
            if attempt < max_attempts and ('429' in msg or 'rate limit' in msg.lower()):
                st.warning(f'TPM limit hit. Waiting 65 s, then resuming from last checkpoint (attempt {attempt + 1} of {max_attempts}). Keep this tab open.')
                time.sleep(65)
                continue
            raise

    dec = decision if isinstance(decision, str) else str(decision)
    st.divider()
    st.subheader(f'Results — {ticker} · {d.strftime("%d %b %Y")}')
    st.metric('Decision', dec)

    reports = [
        ('Market', 'market_report'),
        ('Sentiment', 'sentiment_report'),
        ('News', 'news_report'),
        ('Fundamentals', 'fundamentals_report'),
        ('Bull/Bear Debate', 'investment_debate_state'),
        ('Risk Judge', 'risk_debate_state'),
        ('Trader Plan', 'trader_investment_plan'),
        ('Final Decision', 'final_trade_decision'),
    ]
    left, right = st.columns(2)
    for i, (title, key) in enumerate(reports):
        target = left if i % 2 == 0 else right
        with target:
            with st.expander(title, expanded=(title == 'Final Decision')):
                st.write(str(final_state.get(key, 'N/A')))
