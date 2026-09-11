"""CLI smoke test for the goal pipeline — real market data, regex intent, no LLM.

Usage:
    python scripts/demo_goal.py "I want to invest 20000 in indian market or crypto market short term"
    python scripts/demo_goal.py --amount 50000 --market crypto --risk high
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, 'reconfigure'):          # Windows console → Bengali-safe
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from portfolio import allocate as al            # noqa: E402
from portfolio import backtest as bt            # noqa: E402
from portfolio import intent as it              # noqa: E402
from portfolio import narrate as nr             # noqa: E402
from portfolio import screener as sc            # noqa: E402
from portfolio.data import fetch_fx_usdinr, fetch_history   # noqa: E402
from portfolio.universe import BENCHMARKS, UNIVERSES        # noqa: E402


def main(argv):
    text = ' '.join(a for a in argv if not a.startswith('--'))
    spec = it.parse_intent(text, api_key=None)
    for arg in argv:
        if arg.startswith('--amount='):
            spec.amount_inr = float(arg.split('=', 1)[1])
        if arg.startswith('--market='):
            spec.markets = {'india': ['india'], 'crypto': ['crypto'],
                            'both': ['india', 'crypto']}.get(arg.split('=', 1)[1],
                                                             spec.markets)
        if arg.startswith('--risk='):
            spec.risk = arg.split('=', 1)[1]
        if arg.startswith('--horizon='):
            spec.horizon = arg.split('=', 1)[1]

    print('GOAL SPEC:', spec.to_dict())
    frames = fetch_history([t for m in spec.markets for t in UNIVERSES[m]]
                           + [BENCHMARKS[m] for m in spec.markets])
    fx = fetch_fx_usdinr()
    print('FX USD/INR = {:.2f}; {} tickers fetched'.format(fx, len(frames)))
    if not frames:
        print('NO DATA — check network.')
        return 1

    if len(spec.markets) == 1:
        frac = {m: 1.0 for m in spec.markets}
    else:
        india, crypto = al.RISK_SPLIT.get(spec.risk, (0.60, 0.40))
        frac = {'india': india, 'crypto': crypto}
    plans, backtests = {}, {}
    for market in spec.markets:
        rows = []
        for ticker, df in frames.items():
            if ticker in UNIVERSES[market]:
                metrics = sc.compute_metrics(df, market)
                if metrics:
                    metrics['ticker'] = ticker
                    metrics['name'] = UNIVERSES[market][ticker]
                    rows.append(metrics)
        table = sc.score_universe(rows, spec.horizon)
        picks = sc.shortlist(table, spec.risk, spec.top_n)
        amount = spec.amount_inr * frac[market]
        plan = al.build_portfolio(picks, amount, spec.risk, market, fx)
        plans[market] = plan
        closes_df = {t: f['Close'] for t, f in frames.items()
                     if t in UNIVERSES[market] or t == BENCHMARKS[market]}
        import pandas as pd
        backtests[market] = bt.walk_forward(pd.DataFrame(closes_df), market,
                                            sc.RISK_MAX_VOL[spec.risk],
                                            k=max(len(picks), 3),
                                            benchmark=BENCHMARKS[market])

    print()
    print(nr.narrate_plan(spec.to_dict(), plans, backtests, api_key=None))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
