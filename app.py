import streamlit as st
import yfinance as yf
import os
import time
import html
from datetime import date, timedelta
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from discovery import load_universe, rank_stocks

st.set_page_config(page_title='Sanjib Market Intelligence', page_icon='✦', layout='wide', initial_sidebar_state='collapsed')

st.markdown('''
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;500;600&display=swap');
:root{--void:#000;--white:#fff;--ash:#9a9a9a;--mist:#bdbdbd;--iris:#8052ff;--amber:#ffb829;--green:#15846e}
.stApp{background:#000;color:#fff;font-family:Inter,ui-sans-serif,system-ui,sans-serif}
.block-container{max-width:1280px;padding:24px 28px 80px}
header[data-testid="stHeader"]{background:rgba(0,0,0,0);height:0}
.hero{min-height:520px;display:grid;grid-template-columns:minmax(0,1fr) minmax(360px,.9fr);gap:48px;align-items:center;padding:72px 0 56px;border-bottom:1px solid rgba(255,255,255,.08)}
.eyebrow,.section-label{font-size:12px;line-height:1.5;letter-spacing:.08em;text-transform:uppercase;font-weight:600;color:var(--amber)}
.hero-title{font-size:clamp(56px,8vw,108px);line-height:.91;letter-spacing:-.055em;font-weight:400;margin:18px 0 28px;max-width:760px}
.hero-copy{font-size:18px;line-height:1.5;font-weight:200;color:#d0d0d0;max-width:560px}
.status-row{display:flex;gap:24px;flex-wrap:wrap;margin-top:30px;color:var(--ash);font-size:12px}
.status-pill{background:none;border:0;padding:0}.dot{width:6px;height:6px;border-radius:50%;background:#44d7a3;display:inline-block;margin-right:7px;box-shadow:0 0 12px rgba(68,215,163,.7)}
.constellation{height:430px;position:relative;overflow:hidden;filter:drop-shadow(0 0 18px rgba(128,82,255,.18))}
.constellation:before{content:'';position:absolute;inset:5% 5%;background:radial-gradient(ellipse at 45% 48%,rgba(128,82,255,.13),transparent 48%),radial-gradient(circle at 70% 32%,rgba(255,184,41,.09),transparent 22%),radial-gradient(circle at 30% 70%,rgba(21,132,110,.10),transparent 25%)}
.p{position:absolute;width:4px;height:4px;clip-path:polygon(50% 0,100% 100%,0 100%);background:var(--c);opacity:.8;transform:rotate(var(--r)) scale(var(--s));animation:float var(--t) ease-in-out infinite alternate}
@keyframes float{to{transform:translate(7px,-9px) rotate(var(--r)) scale(var(--s))}}
.nav{display:flex;align-items:center;justify-content:space-between;padding:20px 0 12px}
.brand{font-size:16px;font-weight:500;letter-spacing:-.02em}.brand-mark{display:inline-block;color:var(--iris);margin-right:8px;font-size:20px}
.nav-right{color:var(--ash);font-size:12px;letter-spacing:.08em;text-transform:uppercase}
.section{padding:72px 0}.section-head{display:grid;grid-template-columns:1fr 1fr;gap:60px;align-items:start;margin-bottom:36px}.section-title{font-size:clamp(38px,5vw,64px);line-height:1;letter-spacing:-.05em;font-weight:400;margin:8px 0}.section-copy{font-size:18px;line-height:1.5;font-weight:200;color:var(--mist);max-width:520px}
.nav-card{padding:0 0 18px;margin-bottom:12px;border-bottom:1px solid rgba(255,255,255,.08)}.nav-title{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--ash);margin-bottom:8px}.nav-caption{font-size:11px;color:#666;margin-top:7px}
/* Streamlit controls: keep the Dala-like void while retaining functional controls. */
div[data-baseweb="select"]>div{background:#080808;border:1px solid rgba(255,255,255,.16);border-radius:24px;color:#fff;min-height:44px}
div[data-baseweb="select"] span{color:#fff}
.stTextInput input,.stDateInput input{background:#080808;color:#fff;border:1px solid rgba(255,255,255,.16);border-radius:24px}
.stSlider [data-baseweb="slider"]{color:var(--iris)}
.stButton>button{background:var(--iris);color:#fff;border:0;border-radius:24px;min-height:44px;font-weight:600;font-size:13px;padding:0 18px}
.stButton>button:hover{background:#9069ff;color:#fff;border:0}
.stDownloadButton>button{background:transparent;color:#fff;border:1px solid rgba(255,255,255,.18);border-radius:24px}
.stDownloadButton>button:hover{border-color:var(--iris);color:#fff}
.stCheckbox label,.stRadio label,.stSelectbox label,.stTextInput label,.stDateInput label,.stSlider label{color:#9a9a9a!important;font-size:12px!important}
div[data-testid="stVerticalBlockBorderWrapper"]{background:transparent;border:1px solid rgba(255,255,255,.10);border-radius:24px;padding:8px}
div[data-testid="stExpander"]{border:0;border-bottom:1px solid rgba(255,255,255,.10);border-radius:0;background:transparent}
div[data-testid="stExpander"] summary{color:#fff}
.stDataFrame{border:1px solid rgba(255,255,255,.10);border-radius:18px;overflow:hidden}
.decision-card{padding:30px 0;border-top:1px solid rgba(255,255,255,.12);border-bottom:1px solid rgba(255,255,255,.12);margin:24px 0 42px}.decision-caption{font-size:12px;text-transform:uppercase;letter-spacing:.1em;color:var(--amber)}.decision-value{font-size:clamp(42px,6vw,72px);font-weight:400;letter-spacing:-.05em;line-height:1;margin-top:10px}.decision-meta{font-size:12px;color:#777;margin-top:14px}
.footer{text-align:center;color:#555;font-size:11px;padding-top:60px}.muted{color:#777;font-size:12px}
@media(max-width:800px){.hero{grid-template-columns:1fr;min-height:auto;padding:48px 0}.constellation{height:250px}.section-head{grid-template-columns:1fr;gap:20px}.hero-title{font-size:58px}.block-container{padding-left:18px;padding-right:18px}}
</style>''', unsafe_allow_html=True)


def build_config():
    cfg=DEFAULT_CONFIG.copy()
    cfg['llm_provider']='google'; cfg['deep_think_llm']='gemini-3.5-flash'; cfg['quick_think_llm']='gemini-3.1-flash-lite'
    cfg['google_thinking_level']='minimal'; cfg['temperature']=0; cfg['max_tokens']=1500; cfg['llm_max_retries']=2
    cfg['news_article_limit']=5; cfg['global_news_article_limit']=3; cfg['max_debate_rounds']=1; cfg['max_risk_discuss_rounds']=1; cfg['checkpoint_enabled']=True
    os.environ['GOOGLE_API_KEY']=st.secrets['GOOGLE_API_KEY']
    return cfg


def is_supported_ticker(ticker):
    ticker=ticker.upper().strip()
    return ticker.endswith('.NS') or ticker.endswith('.BO') or ticker.endswith('-USD')


def run_deep_analysis(ticker,analysis_date):
    ticker=ticker.upper().strip()
    if not is_supported_ticker(ticker): raise ValueError('Unsupported ticker. Use NSE (.NS), BSE (.BO), or crypto (-USD).')
    df=yf.download(ticker,period='3mo',progress=False,multi_level_index=False)
    if df is None or df.empty: raise ValueError('No market data found for '+ticker)
    tg=TradingAgentsGraph(debug=False,config=build_config())
    for attempt in range(1,11):
        try:
            with st.status(f'Agents working · pass {attempt}/10',expanded=True) as status:
                final_state,decision=tg.propagate(ticker,analysis_date); status.update(label='Analysis complete',state='complete')
            return final_state,decision
        except Exception as exc:
            msg=str(exc)
            if attempt<10 and ('429' in msg or 'rate limit' in msg.lower()):
                st.warning(f'Rate limit encountered. Waiting 65 s, then resuming from checkpoint (pass {attempt+1}/10).'); time.sleep(65); continue
            raise
    raise RuntimeError('Analysis did not complete.')


def show_constellation():
    colors=['#8052ff','#ffb829','#15846e','#a56cff','#43a7ff','#ff4f9a','#8052ff']
    pts=[]
    for i in range(85):
        x=(i*47)%92+3; y=(i*73)%84+8; c=colors[i%len(colors)]; r=(i*31)%140; s=0.7+(i%5)*.16; t=2.4+(i%6)*.45
        pts.append(f'<span class="p" style="left:{x}%;top:{y}%;--c:{c};--r:{r}deg;--s:{s};--t:{t}s"></span>')
    return '<div class="constellation">'+''.join(pts)+'</div>'


def show_deep_result(ticker,analysis_date,final_state,decision):
    dec=decision if isinstance(decision,str) else str(decision); low=dec.lower(); badge='🟢' if 'buy' in low else ('🔴' if 'sell' in low else '🟡')
    st.markdown('<div class="section-label">03 · Intelligence result</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="decision-card"><div class="decision-caption">Final portfolio signal</div><div class="decision-value">{badge} {html.escape(dec)}</div><div class="decision-meta">{html.escape(ticker)} · analysis date {html.escape(analysis_date)} · generated by the multi-agent desk</div></div>',unsafe_allow_html=True)
    fd_text=str(final_state.get('final_trade_decision','')); fd_low=fd_text.lower(); brief=''
    if 'executive summary' in fd_low:
        seg=fd_text[fd_low.index('executive summary')+len('executive summary'):].strip().lstrip(' :').strip(); end=seg.lower().find('investment thesis'); brief=(seg[:end] if end!=-1 else seg[:600]).strip()
    if not brief: brief=fd_text[:600].strip()
    brief=brief.replace('**','').replace('__','').strip().strip('*').lstrip(':').strip()
    if brief:
        st.markdown('<div class="section-label">Executive brief</div>',unsafe_allow_html=True); st.write(brief)
    reports=[('Market','market_report','Price action, technical context and market regime.'),('Sentiment','sentiment_report','Investor mood, positioning and sentiment signals.'),('News','news_report','Recent company and market-moving news context.'),('Fundamentals','fundamentals_report','Business quality, financials and valuation context.'),('Bull / Bear Debate','investment_debate_state','Structured opposing-case investment debate.'),('Risk Judge','risk_debate_state','Risk assessment and challenge to the proposed trade.'),('Trader Plan','trader_investment_plan','Action plan derived from the research stack.'),('Final Decision','final_trade_decision','The final synthesized trade decision.')]
    st.markdown('<div class="section-label">04 · Research stack</div>',unsafe_allow_html=True); expand_all=st.toggle('Expand all reports',key=f'expand_all_reports_{ticker}')
    left,right=st.columns(2,gap='large')
    for i,(title,key,description) in enumerate(reports):
        text=str(final_state.get(key,'N/A')); target=left if i%2==0 else right
        with target:
            with st.expander(f'{title} · {len(text.split()):,} words',expanded=(expand_all or title=='Final Decision')): st.caption(description); st.write(text)
    lines=['SANJIB MARKET INTELLIGENCE',f'Ticker: {ticker}',f'Analysis date: {analysis_date}',f'Final portfolio signal: {dec}','']
    for title,key,description in reports: lines.extend([f'## {title}',description,'',str(final_state.get(key,'N/A')),''])
    st.markdown('<div class="section-label">05 · Export</div>',unsafe_allow_html=True)
    st.download_button('Download complete report (.md)',data='\n'.join(lines),file_name=f'{ticker}_{analysis_date.replace(" ","_")}_market_intelligence.md',mime='text/markdown',use_container_width=True)


if not st.session_state.get('auth'):
    st.markdown('<div class="nav"><div class="brand"><span class="brand-mark">✦</span>SANJIB MARKET INTELLIGENCE</div><div class="nav-right">Private research desk</div></div>',unsafe_allow_html=True)
    st.markdown(f'<div class="hero"><div><div class="eyebrow">PRIVATE MULTI-AGENT MARKET INTELLIGENCE</div><div class="hero-title">Think clearly.<br>Trade deliberately.</div><div class="hero-copy">A focused research desk combining market data, sentiment, news, fundamentals, debate, risk and trader planning into one decision workflow.</div><div class="status-row"><span class="status-pill"><span class="dot"></span> Engine online</span><span class="status-pill">Gemini multi-agent</span><span class="status-pill">NSE · BSE · Crypto</span></div></div>{show_constellation()}</div>',unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown('<div class="section-label">Access</div>',unsafe_allow_html=True); st.subheader('Enter the research desk'); user=st.text_input('Username'); pw=st.text_input('Password',type='password')
        if st.button('Enter Analysis Desk',type='primary',use_container_width=True):
            if user==st.secrets['APP_USERNAME'] and pw==st.secrets['APP_PASSWORD']: st.session_state.auth=True; st.rerun()
            else: st.error('Wrong username or password')
    st.markdown('<div class="footer">Sanjib Market Intelligence · Multi-agent decision support</div>',unsafe_allow_html=True); st.stop()

_,header_right=st.columns([6,1])
with header_right:
    if st.button('Logout',use_container_width=True):
        st.session_state.auth=False
        for k in ('analysis_running','analysis_result','discovery_result'): st.session_state.pop(k,None)
        st.rerun()

st.markdown('<div class="nav"><div class="brand"><span class="brand-mark">✦</span>SANJIB MARKET INTELLIGENCE</div><div class="nav-right">LIVE RESEARCH DESK</div></div>',unsafe_allow_html=True)
st.markdown(f'<div class="hero"><div><div class="eyebrow">LIVE MARKET INTELLIGENCE</div><div class="hero-title">Discover.<br>Research.<br>Decide.</div><div class="hero-copy">Quantitative discovery feeds the existing eight-layer multi-agent research desk. The workflow is designed for NSE, BSE and crypto only.</div><div class="status-row"><span class="status-pill"><span class="dot"></span> Engine ready</span><span class="status-pill">Gemini</span><span class="status-pill">Checkpoint protected</span><span class="status-pill">8 intelligence modules</span></div></div>{show_constellation()}</div>',unsafe_allow_html=True)

st.markdown('<div class="nav-card"><div class="nav-title">Workspace</div>',unsafe_allow_html=True)
menu=st.selectbox('Select module',['📊 Market Dashboard','🔎 Discover Stocks','🧠 Deep Analysis','🎯 Goal Portfolio (beta)'],index=0,label_visibility='collapsed')
st.markdown('<div class="nav-caption">Select a module to open its working interface.</div></div>',unsafe_allow_html=True)

if menu=='🔎 Discover Stocks':
    st.markdown('<div class="section"><div class="section-head"><div><div class="section-label">01 · Market discovery</div><div class="section-title">Find the strongest setups.</div></div><div class="section-copy">Screen the supported universe using momentum, trend, RSI, volume, relative strength and risk quality. The ranking is a research filter, not a BUY signal.</div></div>',unsafe_allow_html=True)
    with st.container(border=True):
        c1,c2,c3=st.columns([2.1,1.3,1.3],vertical_alignment='bottom')
        with c1: universe_name=st.selectbox('Market universe',['NSE — Liquid 50','BSE — Liquid 30','Crypto — Large Cap 12'])
        with c2: shortlist_size=st.slider('Candidates to return',5,25,10)
        with c3: discover=st.button('Discover',type='primary',use_container_width=True,disabled=st.session_state.get('analysis_running',False))
    if discover:
        st.session_state.analysis_running=True
        try:
            universe,source_status=load_universe(universe_name)
            with st.status(f'Scanning {len(universe)} symbols…',expanded=True) as status: ranked=rank_stocks(universe); status.update(label='Discovery scan complete',state='complete')
            st.session_state.discovery_result={'universe':universe_name,'source':source_status,'ranked':ranked}
        except Exception as exc: st.error(f'Discovery failed: {exc}')
        finally: st.session_state.analysis_running=False
    discovery=st.session_state.get('discovery_result')
    if discovery:
        ranked=discovery['ranked']; st.info(f"Universe: {discovery['universe']} · Source: {discovery['source']} · {len(ranked)} symbols successfully scored.")
        if ranked.empty: st.error('No usable market data was returned. Try again later.')
        else:
            display=ranked.head(shortlist_size); st.markdown('<div class="section-label">02 · Ranked opportunities</div>',unsafe_allow_html=True); st.dataframe(display,use_container_width=True,hide_index=True)
            with st.container(border=True):
                st.subheader('Deep-analyse a candidate'); selected=st.selectbox('Candidate',display['Ticker'].tolist()); deep=st.button('Run 8-layer Deep Analysis',type='primary',use_container_width=True,disabled=st.session_state.get('analysis_running',False))
            if deep:
                st.session_state.analysis_running=True
                try:
                    selected_date=date.today()-timedelta(days=1); final_state,decision=run_deep_analysis(selected,selected_date.strftime('%Y-%m-%d')); st.session_state.analysis_result={'ticker':selected,'date':selected_date.strftime('%d %b %Y'),'final_state':final_state,'decision':decision}
                except Exception as exc: st.error(f'Deep analysis failed: {exc}')
                finally: st.session_state.analysis_running=False

elif menu=='🧠 Deep Analysis':
    st.markdown('<div class="section"><div class="section-head"><div><div class="section-label">01 · Analysis setup</div><div class="section-title">Research a supported ticker.</div></div><div class="section-copy">Run the full eight-layer desk for an NSE, BSE or crypto instrument. Unsupported markets are rejected before the agent workflow starts.</div></div>',unsafe_allow_html=True)
    with st.container(border=True):
        c1,c2,c3=st.columns([2.2,1.8,1],vertical_alignment='bottom')
        with c1: ticker=st.text_input('Ticker symbol','RELIANCE.NS').upper().strip()
        with c2: d=st.date_input('Analysis date',date.today()-timedelta(days=1))
        with c3: analyze=st.button('Run Analysis',type='primary',use_container_width=True,disabled=st.session_state.get('analysis_running',False))
        st.caption('Supported market scope: NSE (.NS), BSE (.BO) and crypto (-USD).')
    if analyze:
        if not ticker: st.error('Please enter a ticker symbol.'); st.stop()
        if not is_supported_ticker(ticker): st.error('Unsupported ticker. Use NSE (.NS), BSE (.BO), or crypto (-USD).')
        else:
            st.session_state.analysis_running=True
            try:
                final_state,decision=run_deep_analysis(ticker,d.strftime('%Y-%m-%d')); st.session_state.analysis_result={'ticker':ticker,'date':d.strftime('%d %b %Y'),'final_state':final_state,'decision':decision}
            except Exception as exc: st.error(str(exc))
            finally: st.session_state.analysis_running=False

elif menu=='🎯 Goal Portfolio (beta)':
    from goaldesk.app_page import render_portfolio_page
    render_portfolio_page(); st.stop()
else:
    st.markdown('<div class="section"><div class="section-head"><div><div class="section-label">01 · Market dashboard</div><div class="section-title">One desk. One workflow.</div></div><div class="section-copy">Discover opportunities, validate the setup, run the eight-layer research stack and build a budget-aware portfolio plan across India and crypto.</div></div>',unsafe_allow_html=True)
    st.markdown('<div class="section-label">Markets</div><p class="muted">NSE · BSE · Crypto</p>',unsafe_allow_html=True)

result=st.session_state.get('analysis_result')
if result: show_deep_result(result['ticker'],result['date'],result['final_state'],result['decision'])
st.markdown('<div class="footer">Sanjib Market Intelligence · Gemini multi-agent research desk · NSE + BSE + Crypto</div>',unsafe_allow_html=True)
