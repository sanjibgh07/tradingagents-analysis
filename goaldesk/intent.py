"""Natural-language goal → structured GoalSpec.

Gemini handles understanding; strict rules remain as the always-available fallback.
The Indian market key covers the curated NSE + BSE universe; crypto is separate.
"""
import json
import re
from dataclasses import asdict, dataclass

QUICK_MODEL = 'gemini-3.1-flash-lite'
DEFAULT_AMOUNT = 20000.0
VALID_MARKETS = ('india', 'crypto')
VALID_HORIZONS = ('short', 'medium', 'long')
VALID_RISK = ('low', 'medium', 'high')

@dataclass
class GoalSpec:
    amount_inr: float
    markets: list
    horizon: str = 'short'
    risk: str = 'medium'
    top_n: int = None
    source: str = 'rules'
    raw_text: str = ''
    def to_dict(self): return asdict(self)

_NUM = r'(\d[\d,]*(?:\.\d+)?)'
_MULT = r'(k|thousand|হাজার|lakh|lac|লাখ|crore|কোটি|cr|l)?'
AMOUNT_RE = re.compile(r'(?:₹|rs\.?|inr|rupees?|/-)?\s*' + _NUM + r'\s*' + _MULT, re.IGNORECASE)
MULTIPLIERS = {'k':1e3,'thousand':1e3,'হাজার':1e3,'lakh':1e5,'lac':1e5,'লাখ':1e5,'crore':1e7,'কোটি':1e7,'cr':1e7,'l':1e5}
CRYPTO_WORDS = re.compile(r'crypto|coin|bitcoin|btc|ethereum|eth|solan|doge|xrp|ক্রিপ্টো', re.IGNORECASE)
INDIA_WORDS = re.compile(r'indian|india|nse|bse|nifty|sensex|\bstock\b|\bshares?\b|equity|equities|ইন্ডিয়ান|শেয়ার|স্টক', re.IGNORECASE)
SHORT_WORDS = re.compile(r'short|\bweek|\bdays?\b|quick|দ্রুত|শর্ট', re.IGNORECASE)
MEDIUM_WORDS = re.compile(r'month|মাস', re.IGNORECASE)
LONG_WORDS = re.compile(r'\byears?\b|long|বছর|লং', re.IGNORECASE)
LOW_RISK_WORDS = re.compile(r'safe|conservative|low risk|security|নিরাপদ|কম ঝুঁকি', re.IGNORECASE)
HIGH_RISK_WORDS = re.compile(r'aggressive|risky|high risk|moon|বেশি ঝুঁকি', re.IGNORECASE)

def parse_amount(text):
    for match in AMOUNT_RE.finditer(text or ''):
        try: value = float(match.group(1).replace(',', ''))
        except ValueError: continue
        value *= MULTIPLIERS.get((match.group(2) or '').lower(), 1.0)
        if value >= 100: return float(value)
    return None

def parse_intent_rules(text):
    text = text or ''
    markets = []
    if INDIA_WORDS.search(text): markets.append('india')
    if CRYPTO_WORDS.search(text): markets.append('crypto')
    if not markets: markets = ['india']
    if SHORT_WORDS.search(text): horizon = 'short'
    elif MEDIUM_WORDS.search(text): horizon = 'medium'
    elif LONG_WORDS.search(text): horizon = 'long'
    else: horizon = 'short'
    if LOW_RISK_WORDS.search(text): risk = 'low'
    elif HIGH_RISK_WORDS.search(text): risk = 'high'
    else: risk = 'medium'
    return GoalSpec(amount_inr=parse_amount(text) or DEFAULT_AMOUNT, markets=markets, horizon=horizon, risk=risk, top_n=None, source='rules', raw_text=text)

SYSTEM_PROMPT = (
    "You convert a retail investor's natural-language investing goal into strict JSON. "
    'Respond with JSON ONLY. Keys: {"amount_inr": number in INR, "markets": array with values from ["india","crypto"], '
    '"horizon": "short"|"medium"|"long", "risk": "low"|"medium"|"high", "top_n": integer 2-8 or null}. '
    'Indian/NSE/Nifty/BSE/Sensex/stock/share/equity means india; crypto/coin/bitcoin means crypto. '
    'Both/and/or requests may include multiple markets. Safe/conservative means low risk; aggressive/risky means high.'
)

def _extract_json(text):
    if not text: return None
    start, end = text.find('{'), text.rfind('}')
    if start == -1 or end <= start: return None
    try: return json.loads(text[start:end+1])
    except Exception: return None

def _llm_intent(text, api_key):
    from langchain_google_genai import ChatGoogleGenerativeAI
    model = ChatGoogleGenerativeAI(model=QUICK_MODEL, google_api_key=api_key, temperature=0, max_tokens=300)
    response = model.invoke([('system', SYSTEM_PROMPT), ('human', text)])
    data = _extract_json(getattr(response, 'content', None) or str(response)) or {}
    amount = float(data.get('amount_inr') or 0)
    markets = [m for m in (data.get('markets') or []) if m in VALID_MARKETS]
    horizon = data.get('horizon') if data.get('horizon') in VALID_HORIZONS else None
    risk = data.get('risk') if data.get('risk') in VALID_RISK else None
    top_n = data.get('top_n')
    top_n = int(top_n) if isinstance(top_n,(int,float)) and 2 <= top_n <= 8 else None
    if amount < 100 or not markets: raise ValueError('LLM JSON not usable')
    return GoalSpec(amount_inr=min(amount,1e9), markets=markets, horizon=horizon or 'short', risk=risk or 'medium', top_n=top_n, source='llm', raw_text=text)

def parse_intent(text, api_key=None):
    if api_key:
        try: return _llm_intent(text, api_key)
        except Exception: pass
    return parse_intent_rules(text)
