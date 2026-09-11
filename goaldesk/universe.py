"""Curated liquid universes for the goal-based portfolio mode.

Market scope is deliberately limited to NSE, BSE and crypto. Equity tickers use
Yahoo Finance's .NS/.BO suffixes; crypto is quoted in USD and sized in INR.
"""

NSE_UNIVERSE = {
    'RELIANCE.NS': 'Reliance Industries', 'TCS.NS': 'Tata Consultancy Services',
    'HDFCBANK.NS': 'HDFC Bank', 'ICICIBANK.NS': 'ICICI Bank', 'SBIN.NS': 'State Bank of India',
    'AXISBANK.NS': 'Axis Bank', 'KOTAKBANK.NS': 'Kotak Mahindra Bank', 'INFY.NS': 'Infosys',
    'LT.NS': 'Larsen & Toubro', 'ITC.NS': 'ITC', 'HINDUNILVR.NS': 'Hindustan Unilever',
    'TITAN.NS': 'Titan Company', 'BAJFINANCE.NS': 'Bajaj Finance', 'MARUTI.NS': 'Maruti Suzuki',
    'TATASTEEL.NS': 'Tata Steel', 'JSWSTEEL.NS': 'JSW Steel', 'HINDALCO.NS': 'Hindalco Industries',
    'SUNPHARMA.NS': 'Sun Pharma', 'CIPLA.NS': 'Cipla', 'DRREDDY.NS': "Dr Reddy's Laboratories",
    'ASIANPAINT.NS': 'Asian Paints', 'ULTRACEMCO.NS': 'UltraTech Cement', 'GRASIM.NS': 'Grasim Industries',
    'NTPC.NS': 'NTPC', 'POWERGRID.NS': 'Power Grid Corporation', 'ONGC.NS': 'Oil & Natural Gas Corp',
    'COALINDIA.NS': 'Coal India', 'ADANIENT.NS': 'Adani Enterprises', 'ADANIPORTS.NS': 'Adani Ports & SEZ',
    'DMART.NS': 'Avenue Supermarts (DMart)', 'ETERNAL.NS': 'Eternal (Zomato)', 'IRFC.NS': 'Indian Railway Finance Corp',
    'BHARTIARTL.NS': 'Bharti Airtel', 'WIPRO.NS': 'Wipro', 'HCLTECH.NS': 'HCL Technologies',
    'TECHM.NS': 'Tech Mahindra', 'NESTLEIND.NS': 'Nestle India', 'TRENT.NS': 'Trent', 'BEL.NS': 'Bharat Electronics',
}

# Liquid large-cap BSE equivalents. Kept intentionally compact to limit data calls.
BSE_UNIVERSE = {
    ticker.replace('.NS', '.BO'): name for ticker, name in NSE_UNIVERSE.items()
    if ticker not in {'DMART.NS', 'TMPV.NS'}
}

CRYPTO_UNIVERSE = {
    'BTC-USD': 'Bitcoin', 'ETH-USD': 'Ethereum', 'SOL-USD': 'Solana', 'XRP-USD': 'XRP',
    'BNB-USD': 'BNB', 'ADA-USD': 'Cardano', 'AVAX-USD': 'Avalanche', 'LINK-USD': 'Chainlink',
    'DOGE-USD': 'Dogecoin', 'TRX-USD': 'TRON', 'LTC-USD': 'Litecoin', 'BCH-USD': 'Bitcoin Cash',
}

UNIVERSES = {'nse': NSE_UNIVERSE, 'bse': BSE_UNIVERSE, 'crypto': CRYPTO_UNIVERSE}
BENCHMARKS = {'nse': '^NSEI', 'bse': '^BSESN', 'crypto': 'BTC-USD'}
BENCHMARK_LABELS = {'nse': 'NIFTY 50 (^NSEI)', 'bse': 'SENSEX (^BSESN)', 'crypto': 'Bitcoin (BTC-USD)'}
MARKET_LABELS = {'nse': 'Indian stocks (NSE)', 'bse': 'Indian stocks (BSE)', 'crypto': 'Crypto (USD quoted)'}


def names_for(market):
    """Ticker -> display-name mapping for nse, bse or crypto."""
    return UNIVERSES.get(market, {})
