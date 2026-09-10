import streamlit as st
import yfinance as yf
import os
from datetime import date, timedelta
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

if not st.session_state.get('auth'):
    st.title('Trading Agents Analysis')
    user = st.text_input('Username')
    pw = st.text_input('Password', type='password')
    if st.button('Login'):
        if user == st.secrets['APP_USERNAME'] and pw == st.secrets['APP_PASSWORD']:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error('Wrong username or password')
    st.stop()

st.title('Trading Agents Analysis')
ticker = st.text_input('Ticker', 'AAPL').upper()
d = st.date_input('Analysis date', date.today() - timedelta(days=1))

if st.button('Analyze'):
    df = yf.download(ticker, period='3mo', progress=False, multi_level_index=False)
    if df is None or df.empty:
        st.error('No data for ' + ticker)
        st.stop()
    cfg = DEFAULT_CONFIG.copy()
    cfg['llm_provider'] = 'openai'
    cfg['backend_url'] = 'https://api.groq.com/openai/v1'
    cfg['deep_think_llm'] = 'llama-3.3-70b-versatile'
    cfg['quick_think_llm'] = 'llama-3.1-8b-instant'
    cfg['max_debate_rounds'] = 1
    os.environ['GROQ_API_KEY'] = st.secrets['GROQ_API_KEY']
    os.environ['OPENAI_API_KEY'] = st.secrets['GROQ_API_KEY']
    tg = TradingAgentsGraph(debug=False, config=cfg)
    with st.status('Agents working... 5-15 minutes', expanded=True) as s:
        final_state, decision = tg.propagate(ticker, d.strftime('%Y-%m-%d'))
        s.update(label='Done!', state='complete')
    dec = decision if isinstance(decision, str) else str(decision)
    st.metric('Decision', dec)
    for title, key in [('Market', 'market_report'), ('Sentiment', 'sentiment_report'),
                       ('News', 'news_report'), ('Fundamentals', 'fundamentals_report'),
                       ('Bull/Bear Debate', 'investment_debate_state'),
                       ('Risk Judge', 'risk_debate_state'),
                       ('Trader Plan', 'trader_investment_plan'),
                       ('Final Decision', 'final_trade_decision')]:
        with st.expander(title):
            st.write(str(final_state.get(key, 'N/A')))