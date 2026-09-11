"""Curated investment universes for the goal-based portfolio mode.

India pool  = liquid NSE large/mid caps (Yahoo Finance tickers end with .NS).
Crypto pool = liquid coins quoted in USD on Yahoo; INR sizing uses the live
              USD/INR rate fetched from Yahoo (see portfolio/data.py).
Benchmarks  = used for the honest walk-forward comparison.
"""

NSE_UNIVERSE = {
    'RELIANCE.NS': 'Reliance Industries',
    'TCS.NS': 'Tata Consultancy Services',
    'HDFCBANK.NS': 'HDFC Bank',
    'ICICIBANK.NS': 'ICICI Bank',
    'SBIN.NS': 'State Bank of India',
    'AXISBANK.NS': 'Axis Bank',
    'KOTAKBANK.NS': 'Kotak Mahindra Bank',
    'INFY.NS': 'Infosys',
    'LT.NS': 'Larsen & Toubro',
    'ITC.NS': 'ITC',
    'HINDUNILVR.NS': 'Hindustan Unilever',
    'TITAN.NS': 'Titan Company',
    'BAJFINANCE.NS': 'Bajaj Finance',
    'MARUTI.NS': 'Maruti Suzuki',
    'TMPV.NS': 'Tata Motors PV',
    'TATASTEEL.NS': 'Tata Steel',
    'JSWSTEEL.NS': 'JSW Steel',
    'HINDALCO.NS': 'Hindalco Industries',
    'SUNPHARMA.NS': 'Sun Pharma',
    'CIPLA.NS': 'Cipla',
    'DRREDDY.NS': "Dr Reddy's Laboratories",
    'ASIANPAINT.NS': 'Asian Paints',
    'ULTRACEMCO.NS': 'UltraTech Cement',
    'GRASIM.NS': 'Grasim Industries',
    'NTPC.NS': 'NTPC',
    'POWERGRID.NS': 'Power Grid Corporation',
    'ONGC.NS': 'Oil & Natural Gas Corp',
    'COALINDIA.NS': 'Coal India',
    'ADANIENT.NS': 'Adani Enterprises',
    'ADANIPORTS.NS': 'Adani Ports & SEZ',
    'DMART.NS': 'Avenue Supermarts (DMart)',
    'ETERNAL.NS': 'Eternal (Zomato)',
    'IRFC.NS': 'Indian Railway Finance Corp',
    'BHARTIARTL.NS': 'Bharti Airtel',
    'WIPRO.NS': 'Wipro',
    'HCLTECH.NS': 'HCL Technologies',
    'TECHM.NS': 'Tech Mahindra',
    'NESTLEIND.NS': 'Nestle India',
    'TRENT.NS': 'Trent',
    'BEL.NS': 'Bharat Electronics',
}

CRYPTO_UNIVERSE = {
    'BTC-USD': 'Bitcoin',
    'ETH-USD': 'Ethereum',
    'SOL-USD': 'Solana',
    'XRP-USD': 'XRP',
    'BNB-USD': 'BNB',
    'ADA-USD': 'Cardano',
    'AVAX-USD': 'Avalanche',
    'LINK-USD': 'Chainlink',
    'DOGE-USD': 'Dogecoin',
    'TRX-USD': 'TRON',
    'LTC-USD': 'Litecoin',
    'BCH-USD': 'Bitcoin Cash',
}

UNIVERSES = {'india': NSE_UNIVERSE, 'crypto': CRYPTO_UNIVERSE}
BENCHMARKS = {'india': '^NSEI', 'crypto': 'BTC-USD'}
BENCHMARK_LABELS = {'india': 'NIFTY 50 (^NSEI)', 'crypto': 'Bitcoin (BTC-USD)'}
MARKET_LABELS = {'india': 'Indian stocks (NSE)', 'crypto': 'Crypto (USD quoted)'}


def names_for(market):
    """Ticker -> display-name mapping for a market ('india' or 'crypto')."""
    return UNIVERSES.get(market, {})
