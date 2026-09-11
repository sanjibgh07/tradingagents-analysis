"""Turn a screened shortlist into an honest, fully costed portfolio plan.

Handles the two things people with small capital actually hit:
  * affordability — whole shares on NSE, so an unaffordable pick is dropped
    and its money is re-spread (₹20,000 cannot buy a ₹90,000 share);
  * real costs — brokerage, STT and tax (equity STCG 20%, crypto 30%) are
    subtracted from both the target and the stop scenario.
"""
import numpy as np

RISK_CAP = {'low': 0.30, 'medium': 0.35, 'high': 0.40}          # max weight per pick
RISK_SPLIT = {'low': (0.70, 0.30), 'medium': (0.60, 0.40),      # (india, crypto) budget
              'high': (0.45, 0.55)}

STOP_ATR_MULT = {'india': 1.5, 'crypto': 2.0}
STOP_MIN_PCT = {'india': 0.05, 'crypto': 0.08}                  # never tighter than this
STOP_MAX_PCT = {'india': 0.12, 'crypto': 0.25}                  # never wider than this

STOCK_ROUND_TRIP_FLAT = 40.0        # ₹20 brokerage per side (discount brokers)
STOCK_ROUND_TRIP_PCT = 0.0015       # STT 0.1% on sell + misc charges
CRYPTO_ROUND_TRIP_PCT = 0.010       # ~0.25%/side fees + spread + slippage

STCG_TAX = {'india': 0.20, 'crypto': 0.30}                      # short-term capital gains


def inverse_vol_weights(vols, cap):
    """Lower volatility → bigger weight, then cap + renormalise (few passes)."""
    vols = np.asarray(vols, dtype=float)
    vols = np.where(vols > 0, vols, np.nan)
    inv = 1.0 / vols
    w = inv / np.nansum(inv)
    for _ in range(6):
        over = w > cap
        if not over.any():
            break
        w[over] = cap
        free = ~over
        if w[free].sum() > 0:
            w[free] = w[free] / w[free].sum() * (1.0 - w[over].sum())
    return np.nan_to_num(w, nan=0.0)


def _stop_and_target(entry, atr, market):
    mult = STOP_ATR_MULT.get(market, 1.5)
    risk = min(max(mult * atr, entry * STOP_MIN_PCT.get(market, 0.05)),
               entry * STOP_MAX_PCT.get(market, 0.15))
    if not np.isfinite(risk) or risk <= 0:
        risk = entry * STOP_MIN_PCT.get(market, 0.08)
    stop = entry - risk
    target = entry + 2.0 * risk          # 2R reward for 1R risk
    return float(stop), float(target), float(risk)


def _net_outcome(market, alloc, entry, target, stop):
    """₹ outcome at target and at stop, after costs and estimated tax."""
    if market == 'india':
        round_trip = STOCK_ROUND_TRIP_PCT * alloc + STOCK_ROUND_TRIP_FLAT
    else:
        round_trip = CRYPTO_ROUND_TRIP_PCT * alloc
    tax = STCG_TAX.get(market, 0.20)
    gain_target = alloc * (target / entry - 1.0)
    net_target = gain_target - round_trip - tax * max(gain_target, 0.0)
    loss_stop = alloc * (stop / entry - 1.0)                  # negative
    net_stop = loss_stop - round_trip                         # losses offset other gains
    return round(float(net_target), 2), round(float(net_stop), 2), round(float(round_trip), 2)


def build_portfolio(picks, amount, risk='medium', market='india', fx=1.0):
    """picks = screener shortlist rows for ONE market; amount = budget slice (₹).

    Returns dict with `positions`, `invested`, `cash_left`, `market`, `fx`.
    Crypto entry prices are USD on Yahoo and get converted with `fx`.
    """
    positions = []
    if not picks or amount <= 0:
        return {'positions': positions, 'invested': 0.0, 'cash_left': amount,
                'market': market, 'fx': fx}

    cap = RISK_CAP.get(risk, 0.35)
    vols = [p['vol_ann'] for p in picks]
    weights = inverse_vol_weights(vols, cap)

    working = []
    for pick, weight in zip(picks, weights):
        working.append({'pick': pick, 'weight': float(weight)})

    # Whole-share affordability loop (stocks only): drop what cannot be bought,
    # renormalise what is left, at most 3 passes.
    for _ in range(3):
        dropped = False
        total_w = sum(w['weight'] for w in working)
        if total_w <= 0:
            break
        for w in working:
            w['eff_w'] = w['weight'] / total_w
        for w in list(working):
            if market != 'crypto':
                price_inr = float(w['pick']['close'])
                if int((amount * w['eff_w']) // price_inr) < 1:
                    working.remove(w)
                    dropped = True
        if not dropped:
            break

    total_w = sum(w['weight'] for w in working)
    invested = 0.0
    for w in working:
        pick = w['pick']
        weight = w['weight'] / total_w if total_w > 0 else 0.0
        alloc = float(amount * weight)
        entry_usd = float(pick['close'])
        entry = entry_usd * fx if market == 'crypto' else entry_usd
        if entry <= 0:
            continue
        if market == 'crypto':
            qty = round(alloc / entry, 6)
        else:
            qty = int(alloc // entry)
        if qty <= 0:
            continue
        alloc = qty * entry
        stop, target, risk_amt = _stop_and_target(entry, float(pick['atr14']), market)
        net_target, net_stop, round_trip = _net_outcome(market, alloc, entry, target, stop)
        invested += alloc
        positions.append({
            'ticker': pick['ticker'],
            'name': pick.get('name', pick['ticker']),
            'weight': round(float(weight), 4),
            'alloc_inr': round(float(alloc), 2),
            'qty': qty,
            'entry': round(float(entry), 2),
            'stop': round(float(stop), 2),
            'target': round(float(target), 2),
            'risk_per_unit': round(float(risk_amt), 2),
            'vol_ann': round(float(pick['vol_ann']), 4),
            'rsi14': round(float(pick['rsi14']), 1),
            'score': float(pick.get('score', 0.0)),
            'net_at_target': net_target,
            'net_at_stop': net_stop,
            'est_costs': round_trip,
        })

    invested = round(float(invested), 2)
    return {'positions': positions, 'invested': invested,
            'cash_left': round(float(amount) - invested, 2),
            'market': market, 'fx': fx}

