"""Unit tests for the goal-based portfolio package (no network access).

Run:  python -m unittest discover -s tests -v
"""
import unittest

import numpy as np
import pandas as pd

from portfolio import allocate as al
from portfolio import backtest as bt
from portfolio import intent as it
from portfolio import screener as sc


def synth_df(n=130, start=100.0, drift=0.001, vol=0.02, seed=1):
    """Synthetic daily OHLCV frame (geometric random walk)."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(drift, vol, n)
    close = start * np.cumprod(1 + rets)
    high = close * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.004, n)))
    open_ = np.concatenate([[start], close[:-1]])
    volume = rng.integers(2e5, 5e5, n).astype(float)
    idx = pd.bdate_range('2025-01-01', periods=n)
    return pd.DataFrame({'Open': open_, 'High': high, 'Low': low,
                         'Close': close, 'Volume': volume}, index=idx)


def metric_row(ticker, name, close=500.0, vol_ann=0.3, ret1=0.05, ret3=0.10,
               atr=8.0, liq=1e9):
    return {'ticker': ticker, 'name': name, 'close': close, 'vol_ann': vol_ann,
            'ret1m': ret1, 'ret3m': ret3, 'rsi14': 55.0, 'atr14': atr,
            'avg_dollar_vol': liq, 'max_dd90': -0.1}


class TestScreener(unittest.TestCase):
    def test_compute_metrics_good_frame(self):
        m = sc.compute_metrics(synth_df(n=130), 'india')
        self.assertIsNotNone(m)
        for key in ('close', 'ret1m', 'ret3m', 'vol_ann', 'rsi14', 'atr14'):
            self.assertIn(key, m)
            self.assertTrue(np.isfinite(m[key]))

    def test_compute_metrics_rejects_short_frame(self):
        self.assertIsNone(sc.compute_metrics(synth_df(n=40), 'india'))
        self.assertIsNone(sc.compute_metrics(None, 'india'))

    def test_score_universe_sorted_desc(self):
        rows = [metric_row('A', 'A', ret1=0.20, ret3=0.30),
                metric_row('B', 'B', ret1=0.05, ret3=0.08),
                metric_row('C', 'C', ret1=-0.10, ret3=-0.20)]
        scored = sc.score_universe(rows, 'short')
        self.assertEqual(list(scored['ticker']), ['A', 'B', 'C'])

    def test_shortlist_respects_vol_ceiling(self):
        rows = [metric_row('CALM', 'Calm', vol_ann=0.20),
                metric_row('WILD', 'Wild', vol_ann=1.50, ret1=0.5)]
        scored = sc.score_universe(rows, 'short')
        picks = sc.shortlist(scored, 'low')
        self.assertEqual([p['ticker'] for p in picks], ['CALM'])


class TestAllocate(unittest.TestCase):
    def test_weights_sum_to_one_and_respect_cap(self):
        vols = [0.20, 0.30, 0.40, 0.25]
        w = al.inverse_vol_weights(vols, cap=0.30)
        self.assertAlmostEqual(w.sum(), 1.0, places=6)
        self.assertTrue((w <= 0.30 + 1e-9).all())

    def test_portfolio_buys_everything_when_affordable(self):
        rows = [metric_row('A.NS', 'A', close=100.0, vol_ann=0.2),
                metric_row('B.NS', 'B', close=200.0, vol_ann=0.4)]
        plan = al.build_portfolio(rows, 20000.0, 'medium', 'india')
        self.assertEqual(len(plan['positions']), 2)
        invested = sum(p['alloc_inr'] for p in plan['positions'])
        self.assertLessEqual(invested + plan['cash_left'], 20000.0 + 1e-6)
        self.assertGreater(plan['invested'], 15000.0)

    def test_unaffordable_stock_is_dropped(self):
        rows = [metric_row('RICH.NS', 'Rich', close=90000.0, vol_ann=0.2),
                metric_row('OK.NS', 'Ok', close=300.0, vol_ann=0.4)]
        plan = al.build_portfolio(rows, 20000.0, 'medium', 'india')
        tickers = [p['ticker'] for p in plan['positions']]
        self.assertNotIn('RICH.NS', tickers)
        self.assertEqual(tickers, ['OK.NS'])

    def test_crypto_fractional_with_fx(self):
        rows = [metric_row('BTC-USD', 'Bitcoin', close=60000.0, vol_ann=0.5)]
        plan = al.build_portfolio(rows, 20000.0, 'medium', 'crypto', fx=88.0)
        pos = plan['positions'][0]
        self.assertGreater(pos['qty'], 0)
        self.assertLess(pos['qty'], 1.0)
        self.assertAlmostEqual(pos['entry'], 60000.0 * 88.0, places=4)

    def test_stop_target_costs(self):
        rows = [metric_row('A.NS', 'A', close=100.0, vol_ann=0.2, atr=2.0)]
        plan = al.build_portfolio(rows, 20000.0, 'medium', 'india')
        pos = plan['positions'][0]
        self.assertLess(pos['stop'], pos['entry'])
        self.assertGreater(pos['target'], pos['entry'])
        gross = pos['alloc_inr'] * (pos['target'] / pos['entry'] - 1)
        self.assertLess(pos['net_at_target'], gross)


class TestIntentRules(unittest.TestCase):
    def test_full_sentence_both_markets(self):
        spec = it.parse_intent_rules(
            'I want to invest 20000 in indian market or crypto market, '
            'good return stocks or coins in short period of time')
        self.assertEqual(spec.amount_inr, 20000)
        self.assertEqual(spec.markets, ['india', 'crypto'])
        self.assertEqual(spec.horizon, 'short')

    def test_rupee_comma_and_k(self):
        self.assertEqual(it.parse_amount('₹20,000/-'), 20000.0)
        self.assertEqual(it.parse_amount('50k crypto'), 50000.0)
        self.assertEqual(it.parse_amount('2 lakh in stocks'), 200000.0)
        self.assertEqual(it.parse_amount('1.5 cr'), 15000000.0)

    def test_safe_crypto(self):
        spec = it.parse_intent_rules('₹50,000 bitcoin only, safe')
        self.assertEqual(spec.amount_inr, 50000)
        self.assertEqual(spec.markets, ['crypto'])
        self.assertEqual(spec.risk, 'low')

    def test_long_aggressive(self):
        spec = it.parse_intent_rules('2 lakh in stocks for this year, aggressive')
        self.assertEqual(spec.horizon, 'long')
        self.assertEqual(spec.risk, 'high')
        self.assertEqual(spec.markets, ['india'])

    def test_defaults_when_nothing_matches(self):
        spec = it.parse_intent_rules('help me invest')
        self.assertEqual(spec.amount_inr, it.DEFAULT_AMOUNT)
        self.assertEqual(spec.markets, ['india'])

    def test_parse_intent_never_raises_without_key(self):
        spec = it.parse_intent('invest 30000 in crypto', api_key=None)
        self.assertEqual(spec.amount_inr, 30000)
        self.assertEqual(spec.markets, ['crypto'])


class TestBacktest(unittest.TestCase):
    def _matrix(self):
        cols = {}
        for i, drift in enumerate([0.004, 0.002, 0.0005, -0.001, 0.003]):
            cols[f'T{i}'] = synth_df(n=150, drift=drift, seed=i + 1)['Close']
        return pd.DataFrame(cols)

    def test_walk_forward_returns_sane_metrics(self):
        result = bt.walk_forward(self._matrix(), 'india', risk_max_vol=0.70, k=3)
        self.assertIsNotNone(result)
        self.assertTrue(np.isfinite(result['total']))
        self.assertTrue(0.0 <= result['win_rate'] <= 1.0)
        self.assertGreaterEqual(result['n_rebalances'], 1)
        self.assertLessEqual(result['max_dd'], 0.0)
        self.assertGreater(len(result['curve']), 0)

    def test_too_short_data_returns_none(self):
        short = self._matrix().iloc[:50]
        self.assertIsNone(bt.walk_forward(short, 'india'))

    def test_benchmark_present(self):
        closes = self._matrix()
        closes['BENCH'] = synth_df(n=150, drift=0.001, seed=9)['Close']
        result = bt.walk_forward(closes, 'india', benchmark='BENCH')
        self.assertIsNotNone(result['bench_total'])


if __name__ == '__main__':
    unittest.main()

