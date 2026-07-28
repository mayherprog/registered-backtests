"""
Engine 1 backtester for trading-plan-hybrid.md audit (prove-the-plan).
All rule parameters live in CONFIG so sensitivity/Phase-2 runs reuse identical code.

No-look-ahead contract:
  - A signal computed from data through day t executes at day t+1's OPEN.
  - All indicator values used for the day-t signal use closes up to and including t,
    but NEVER day t+1 data.
  - Exits are evaluated on day t's CLOSE marks and fill at that close (gap risk noted
    in the report, this flatters stops).
  - Within a single day the simulation runs open-then-close: entries fill at the open
    against cash, position slots and kill state as of the PREVIOUS close; exits and
    the mark-to-market follow at that day's close. A position opened at the open of
    day t is therefore marked (and can stop out) at the close of day t.

Option pricing: Black-Scholes call, sigma = M * RV63(underlying), r = 0.04.
M calibrated to the 2026-07-17 OPRA surface (see DATA_NOTES.md). No dividends
(adjusted prices already fold dividends into the return series).
"""
import csv, math, os
from math import log, sqrt, exp, erf

DATA = os.path.join(os.path.dirname(__file__), "..", "data")

BASE_CONFIG = dict(
    symbols=["SPY", "QQQ", "SMH", "XBI", "IWM"],
    bankroll=2100.0,
    target_size=500.0, size_min=400.0, size_max=700.0,
    fixed_size=None,            # if set (e.g. 500), overrides min/max band logic
    max_positions=3, max_per_sector=2, max_entries_per_day=1,
    stop_frac=0.50,             # exit at -50% of premium
    profit_take=1.00,           # +100% -> sell half
    half_off=True,
    dte=50, delta_target=0.50,
    max_hold=40, exit_dte=10,
    blackout=True,              # no entry day-before through day-of FOMC/CPI
    iv_filter=True,             # RV-rank proxy > 0.60 -> halve size
    iv_rank_cut=0.60, iv_action="halve",   # or "skip"
    kill_frac=0.30, kill_pause=10,         # -30% floor
    kill_mode="plan",           # "plan": trip->pause+reset ref, permanent halt at account floor; "reset"; "off"
    account_floor_total=2500.0, other_nlv=1475.0,  # futures $1000 + buffer $475
    spread_frac=0.025,          # half-spread cost each way, fraction of premium
    vol_mult=1.08,              # sigma = vol_mult * RV63
    infinite_bankroll=False,    # diagnostic: constant sizing, ignore cash/afford limits
    riskfree=0.04,
    triggers=dict(reclaim50=True, higher_low=True, xbi_breakout=True, xbi_support=True),
    reclaim_hold=2,             # sessions above MA50 required
    ma_len=50, breakout_len=20,
    cooldown=5,
    use_invalidation=True,      # thesis-invalidation exit on/off
    vol_size_ref=None,          # e.g. 0.20: size = target * ref/RV63, clamped [0.5x, 1.4x]
    dd_throttle=None,           # e.g. 0.15: halve size while equity < (1-x)*peak
    be_trail=False,             # after +50% mark, exit if mark falls to entry premium
    entry_buffer=0.0,           # reclaim requires close > MA50*(1+buffer)
    trend_filter=None,          # e.g. 200: entries only when close > MA200
    sector={"SPY": "broad", "QQQ": "broad", "SMH": "semis", "XBI": "biotech", "IWM": "smallcap"},
)

# ---------- math ----------
def N(x): return 0.5 * (1 + erf(x / sqrt(2)))

def bs_call(S, K, T, r, sig):
    if T <= 0: return max(S - K, 0.0)
    if sig <= 0: return max(S - K * exp(-r * T), 0.0)
    d1 = (log(S / K) + (r + sig * sig / 2) * T) / (sig * sqrt(T))
    d2 = d1 - sig * sqrt(T)
    return S * N(d1) - K * exp(-r * T) * N(d2)

def call_delta(S, K, T, r, sig):
    if T <= 0 or sig <= 0: return 1.0 if S > K else 0.0
    d1 = (log(S / K) + (r + sig * sig / 2) * T) / (sig * sqrt(T))
    return N(d1)

def strike_for_delta(S, T, r, sig, delta):
    """Solve K such that call delta == target, then round to a realistic grid."""
    lo, hi = S * 0.5, S * 2.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if call_delta(S, mid, T, r, sig) > delta: lo = mid
        else: hi = mid
    k = (lo + hi) / 2
    grid = 1.0 if S < 200 else 5.0
    return round(k / grid) * grid

# ---------- data ----------
def load_series(sym):
    rows = list(csv.DictReader(open(os.path.join(DATA, f"{sym.lower()}.csv"))))
    return dict(
        dates=[r["date"] for r in rows],
        o=[float(r["open"]) for r in rows],
        h=[float(r["high"]) for r in rows],
        l=[float(r["low"]) for r in rows],
        c=[float(r["close"]) for r in rows],
    )

def load_events():
    fomc = {r["decision_date"] for r in csv.DictReader(open(os.path.join(DATA, "fomc_dates.csv")))}
    cpi = {r["release_date"] for r in csv.DictReader(open(os.path.join(DATA, "cpi_dates.csv")))}
    return fomc | cpi

def rolling_rv(c, window):
    """Annualized realized vol of log returns over `window` days; value at i uses
    closes [i-window .. i] (inclusive), i.e. only past data."""
    out = [None] * len(c)
    rets = [None] + [log(c[i] / c[i - 1]) for i in range(1, len(c))]
    for i in range(window, len(c)):
        seg = rets[i - window + 1:i + 1]
        m = sum(seg) / len(seg)
        var = sum((x - m) ** 2 for x in seg) / (len(seg) - 1)
        out[i] = sqrt(var) * sqrt(252)
    return out

def rolling_ma(c, n):
    out = [None] * len(c)
    s = 0.0
    for i, x in enumerate(c):
        s += x
        if i >= n: s -= c[i - n]
        if i >= n - 1: out[i] = s / n
    return out

def rolling_max(h, n):
    """max of PRIOR n bars (excluding today) — used for breakout levels."""
    out = [None] * len(h)
    for i in range(n, len(h)):
        out[i] = max(h[i - n:i])
    return out

def rolling_min(l, n):
    out = [None] * len(l)
    for i in range(n, len(l)):
        out[i] = min(l[i - n:i])
    return out

def rv_rank(rv, lookback=252):
    """Percentile rank of today's RV vs prior `lookback` values (past only)."""
    out = [None] * len(rv)
    for i in range(len(rv)):
        if rv[i] is None: continue
        past = [x for x in rv[max(0, i - lookback):i] if x is not None]
        if len(past) < 60: continue
        out[i] = sum(1 for x in past if x < rv[i]) / len(past)
    return out

def swing_lows(l, wing=2):
    """Swing low at i if l[i] is strictly the minimum of l[i-wing..i+wing].
    Confirmed at bar i+wing (usable only from i+wing onward)."""
    marks = []  # (confirm_index, swing_index, swing_low_value)
    for i in range(wing, len(l) - wing):
        seg = l[i - wing:i + wing + 1]
        if l[i] == min(seg) and seg.count(l[i]) == 1:
            marks.append((i + wing, i, l[i]))
    return marks

# ---------- signal generation ----------
def build_signals(series, cfg):
    """Return per-symbol list of (signal_index, trigger_name, invalidation_level).
    signal at index t -> entry at t+1 open. All inputs use data through t only."""
    sigs = {}
    for sym in cfg["symbols"]:
        s = series[sym]
        c, l, h = s["c"], s["l"], s["h"]
        ma = rolling_ma(c, cfg["ma_len"])
        hi20 = rolling_max(h, cfg["breakout_len"])
        lo20 = rolling_min(l, cfg["breakout_len"])
        sw = swing_lows(l)
        confirmed = {}          # confirm_index -> (swing_index, value)
        for ci, si, v in sw: confirmed[ci] = (si, v)
        out = []
        hold = cfg["reclaim_hold"]
        ma_tf = rolling_ma(c, cfg["trend_filter"]) if cfg.get("trend_filter") else None
        start_t = max(cfg["ma_len"] + 5, (cfg.get("trend_filter") or 0) + 1)
        for t in range(start_t, len(c)):
            if ma[t] is None: continue
            if ma_tf is not None and (ma_tf[t] is None or c[t] <= ma_tf[t]): continue
            # 1) 50-day reclaim held `hold` sessions, after being below within 10 sessions
            if cfg["triggers"]["reclaim50"]:
                above = all(c[t - k] > ma[t - k] for k in range(hold))
                prev_below = any(c[t - hold - k] < ma[t - hold - k] for k in range(1, 11)
                                 if ma[t - hold - k] is not None)
                if above and prev_below and c[t] > ma[t] * (1 + cfg.get("entry_buffer", 0.0)):
                    out.append((t, "reclaim50", ma[t]))
            # 2) higher low above prior swing low, confirmed today
            if cfg["triggers"]["higher_low"] and t in confirmed:
                si, v = confirmed[t]
                prior = [(cj, sj, vj) for cj, sj, vj in sw if cj < t]
                if prior:
                    _, _, pv = prior[-1]
                    if v > pv and c[t] > c[si]:
                        out.append((t, "higher_low", v))
            # 3) XBI-only: 20d breakout / support-hold
            if sym == "XBI":
                if cfg["triggers"]["xbi_breakout"] and hi20[t] is not None and \
                        c[t] > hi20[t] and c[t - 1] <= (hi20[t - 1] or 1e18):
                    out.append((t, "xbi_breakout", hi20[t]))
                if cfg["triggers"]["xbi_support"] and lo20[t] is not None and \
                        l[t] <= lo20[t] * 1.01 and c[t] > s["o"][t]:
                    out.append((t, "xbi_support", lo20[t]))
        sigs[sym] = out
    return sigs

# ---------- portfolio simulation ----------
class Position:
    __slots__ = ("sym", "trigger", "entry_i", "K", "expiry_i_T", "entry_prem",
                 "contracts", "half_done", "inval", "cost", "entry_date", "sig_i",
                 "received", "hit50")
    def __init__(self, **kw):
        for k, v in kw.items(): setattr(self, k, v)

def run_backtest(series, cfg, start_date=None, end_date=None, events=None,
                 trade_log=None):
    """Simulate the portfolio. Returns dict with equity curve, trades, stats."""
    dates = series[cfg["symbols"][0]]["dates"]
    idx = {d: i for i, d in enumerate(dates)}
    i0 = idx[min(d for d in dates if (start_date is None or d >= start_date))]
    i1 = idx[max(d for d in dates if (end_date is None or d <= end_date))]
    i0 = max(i0, 70)  # indicator warmup

    rv63 = {s: rolling_rv(series[s]["c"], 63) for s in cfg["symbols"]}
    rv21 = {s: rolling_rv(series[s]["c"], 21) for s in cfg["symbols"]}
    ivr = {s: rv_rank(rv21[s]) for s in cfg["symbols"]}
    sigs = build_signals(series, cfg)
    sig_by_day = {}
    for sym, lst in sigs.items():
        for t, trig, inval in lst:
            sig_by_day.setdefault(t, []).append((sym, trig, inval))

    events = events or set()
    ev_idx = {i for i, d in enumerate(dates) if d in events}
    blocked = set()
    for i in ev_idx:
        blocked.add(i)
        blocked.add(i - 1)  # day before event

    cash = cfg["bankroll"]
    kill_ref = cfg["bankroll"]
    positions, closed, equity_curve = [], [], []
    kill_until, kill_trips = -1, []
    halted = False
    last_sig = {}   # cooldown per symbol
    skipped = dict(afford=0, concurrency=0, blackout=0, ivskip=0, cooldown=0, sector=0, daily=0)

    def mark(pos, i, at_open=False):
        s = series[pos.sym]
        S = s["o"][i] if at_open else s["c"][i]
        # sigma uses data through i-1 for open marks, through i for close marks:
        j = i - 1 if at_open else i
        sig = cfg["vol_mult"] * (rv63[pos.sym][j] or 0.3)
        T = max(pos.expiry_i_T - i, 0) / 252.0
        return bs_call(S, pos.K, T, cfg["riskfree"], sig)

    for i in range(i0, i1 + 1):
        # ---- entries from yesterday's signals, at today's open ----
        # Chronology: the open of day i precedes the close of day i, so this block
        # runs FIRST and sees cash, open positions and kill state exactly as they
        # stood at the close of day i-1. Nothing that happens later today is
        # visible here. (Before 2026-07-28 this block ran after the close-of-day
        # exits, which let an entry be funded by proceeds that had not settled and
        # let a slot freed at the close be reused at that morning's open.)
        todays = sig_by_day.get(i - 1, [])
        if cfg["blackout"] and i in blocked:
            skipped["blackout"] += len(todays)
        elif i <= kill_until or halted:
            pass
        else:
            entered_today = 0
            for sym, trig, inval in todays:
                if entered_today >= cfg["max_entries_per_day"]:
                    skipped["daily"] += 1; continue
                if len(positions) >= cfg["max_positions"]:
                    skipped["concurrency"] += 1; continue
                sec = cfg["sector"][sym]
                if sum(1 for p in positions if cfg["sector"][p.sym] == sec) >= cfg["max_per_sector"]:
                    skipped["sector"] += 1; continue
                if sym in last_sig and i - last_sig[sym] < cfg["cooldown"]:
                    skipped["cooldown"] += 1; continue
                if any(p.sym == sym for p in positions):
                    skipped["cooldown"] += 1; continue
                target = cfg["fixed_size"] or cfg["target_size"]
                if cfg.get("vol_size_ref") and rv63[sym][i - 1]:
                    f = cfg["vol_size_ref"] / rv63[sym][i - 1]
                    target *= min(1.4, max(0.5, f))
                if cfg.get("dd_throttle"):
                    peak = max(v for _, v in equity_curve) if equity_curve else cfg["bankroll"]
                    cur = equity_curve[-1][1] if equity_curve else cfg["bankroll"]
                    if cur < (1 - cfg["dd_throttle"]) * peak:
                        target *= 0.5
                if cfg["iv_filter"] and ivr[sym][i - 1] is not None and ivr[sym][i - 1] > cfg["iv_rank_cut"]:
                    if cfg["iv_action"] == "skip":
                        skipped["ivskip"] += 1; continue
                    target = target / 2
                S = series[sym]["o"][i]
                sigv = cfg["vol_mult"] * (rv63[sym][i - 1] or None)
                if not sigv: continue
                T = cfg["dte"] / 365.0
                K = strike_for_delta(S, T, cfg["riskfree"], sigv, cfg["delta_target"])
                prem = bs_call(S, K, T, cfg["riskfree"], sigv)
                per = prem * 100
                if cfg["fixed_size"]:
                    n = max(1, round(cfg["fixed_size"] / per)) if per <= cfg["size_max"] else 0
                    if n * per > cfg["size_max"] * 1.4: n = 0   # fixed still respects sanity
                else:
                    if per > cfg["size_max"]: n = 0
                    else:
                        n = max(1, round(target / per))
                        while n * per > cfg["size_max"]: n -= 1
                        if n * per < cfg["size_min"] and (n + 1) * per <= cfg["size_max"]: n += 1
                if n <= 0 or (not cfg["infinite_bankroll"] and per > cash):
                    skipped["afford"] += 1; continue
                cost = n * per
                if not cfg["infinite_bankroll"] and cost > cash:
                    skipped["afford"] += 1; continue
                cost *= (1 + cfg["spread_frac"])   # entry at ask side
                cash -= cost
                expiry_T = i + int(cfg["dte"] * 252 / 365)   # trading-day expiry index
                positions.append(Position(sym=sym, trigger=trig, entry_i=i, K=K,
                                          expiry_i_T=expiry_T, entry_prem=prem, contracts=n,
                                          half_done=False, inval=inval, cost=cost, received=0.0, hit50=False,
                                          entry_date=dates[i], sig_i=i - 1))
                last_sig[sym] = i
                entered_today += 1

        # ---- exits on today's close ----
        for pos in positions[:]:
            m = mark(pos, i)
            held = i - pos.entry_i
            s = series[pos.sym]
            reason = None
            if cfg["be_trail"] and m >= 1.5 * pos.entry_prem: pos.hit50 = True
            if m <= (1 - cfg["stop_frac"]) * pos.entry_prem: reason = "stop"
            elif cfg["be_trail"] and pos.hit50 and m <= pos.entry_prem: reason = "be_trail"
            elif cfg["use_invalidation"] and pos.inval is not None and s["c"][i] < pos.inval: reason = "invalidation"
            elif held >= cfg["max_hold"] or (pos.expiry_i_T - i) <= cfg["exit_dte"] * 252 // 365:
                reason = "time"
            elif cfg["half_off"] and not pos.half_done and m >= (1 + cfg["profit_take"]) * pos.entry_prem:
                sell = pos.contracts // 2 if pos.contracts > 1 else 0
                if sell:
                    cash_in = sell * m * 100 * (1 - cfg["spread_frac"])
                    cash += cash_in
                    pos.received += cash_in
                    pos.contracts -= sell
                    pos.half_done = True
                else:
                    reason = "target_full"   # 1 contract: full exit at +100%
            if reason:
                proceeds = pos.contracts * m * 100 * (1 - cfg["spread_frac"])
                cash += proceeds
                pos.received += proceeds
                closed.append(dict(sym=pos.sym, trigger=pos.trigger,
                                   entry_date=dates[pos.entry_i], exit_date=dates[i],
                                   entry_prem=pos.entry_prem, exit_prem=m,
                                   contracts_final=pos.contracts, cost=pos.cost,
                                   pnl=pos.received - pos.cost,
                                   half_done=pos.half_done, reason=reason, held=held))
                positions.remove(pos)

        # recompute equity after exits
        equity = cash + sum(mark(p, i) * p.contracts * 100 for p in positions)

        # ---- kill switch ----
        killable = cfg["kill_mode"] != "off"
        floor_val = kill_ref * (1 - cfg["kill_frac"])
        acct_floor = cfg["account_floor_total"] - cfg["other_nlv"]
        if killable and i > kill_until and not halted and equity <= floor_val:
            for pos in positions[:]:
                m = mark(pos, i)
                cash += pos.contracts * m * 100
                closed.append(dict(sym=pos.sym, trigger=pos.trigger,
                                   entry_date=dates[pos.entry_i], exit_date=dates[i],
                                   entry_prem=pos.entry_prem, exit_prem=m,
                                   contracts_final=pos.contracts, cost=pos.cost,
                                   pnl=pos.received + pos.contracts * m * 100 - pos.cost,
                                   half_done=pos.half_done, reason="kill_switch",
                                   held=i - pos.entry_i))
                positions.remove(pos)
            equity = cash
            kill_trips.append(dates[i])
            kill_until = i + cfg["kill_pause"]
            kill_ref = equity          # review resets the reference (both modes)
            if cfg["kill_mode"] == "plan" and equity <= acct_floor:
                halted = True          # account floor: everything stops, permanently

        equity_curve.append((dates[i], equity))

    # liquidate remaining at final close
    for pos in positions:
        m = mark(pos, i1)
        cash += pos.contracts * m * 100
        closed.append(dict(sym=pos.sym, trigger=pos.trigger, entry_date=dates[pos.entry_i],
                           exit_date=dates[i1], entry_prem=pos.entry_prem, exit_prem=m,
                           contracts_final=pos.contracts, cost=pos.cost,
                           pnl=pos.received + pos.contracts * m * 100 - pos.cost,
                           half_done=pos.half_done, reason="eod_liquidate",
                           held=i1 - pos.entry_i))
    return dict(equity=equity_curve, trades=closed, skipped=skipped,
                kill_trips=kill_trips, final=equity_curve[-1][1] if equity_curve else cfg["bankroll"])

# ---------- stats ----------
def stats(result, bankroll, stop_frac=0.5):
    eq = [v for _, v in result["equity"]]
    trades = result["trades"]
    if not eq: return {}
    peak, mdd = eq[0], 0.0
    for v in eq:
        peak = max(peak, v)
        mdd = max(mdd, (peak - v) / peak)
    wins = [t for t in trades if t["pnl"] > 0]
    rets = []
    for j in range(1, len(eq)):
        if eq[j - 1] > 0: rets.append(eq[j] / eq[j - 1] - 1)
    import statistics as st
    vol = st.pstdev(rets) * sqrt(252) if len(rets) > 2 else 0
    years = len(eq) / 252
    cagr = (eq[-1] / bankroll) ** (1 / years) - 1 if years > 0 and eq[-1] > 0 else -1
    rs = [t["pnl"] / (stop_frac * t["cost"]) for t in trades if t["cost"] > 0]
    avg_r = sum(rs) / len(rs) if rs else 0
    return dict(final=round(eq[-1], 0), total_return=round(eq[-1] / bankroll - 1, 3),
                cagr=round(cagr, 3), max_dd=round(mdd, 3),
                trades=len(trades), win_rate=round(len(wins) / len(trades), 3) if trades else None,
                avg_pnl=round(sum(t["pnl"] for t in trades) / len(trades), 1) if trades else 0,
                avg_R=round(avg_r, 2), ann_vol=round(vol, 3),
                sharpe=round((cagr) / vol, 2) if vol > 0 else None,
                kill_trips=len(result["kill_trips"]), kill_dates=result["kill_trips"],
                skipped=result["skipped"])

def load_all(cfg=None):
    cfg = cfg or BASE_CONFIG
    return {s: load_series(s) for s in cfg["symbols"]}

if __name__ == "__main__":
    import json, sys
    cfg = dict(BASE_CONFIG)
    series = load_all(cfg)
    ev = load_events()
    res = run_backtest(series, cfg, start_date="2015-01-01", end_date="2026-07-17", events=ev)
    print(json.dumps(stats(res, cfg["bankroll"]), indent=1, default=str))
