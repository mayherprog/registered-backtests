"""Plan C backtester. Spec PRE-REGISTERED in chat 2026-07-18 before any run.
No parameter was changed after seeing results (variant log: A = core-only, C = core+satellite).

CORE ($1,600): weekly (last trading day of week close -> next trading day open),
hold top-2 by 126d return among the 5 ETFs that close above their 200d MA,
equal split of core equity on membership change; exit on dropping from top-2 or
close < MA200 (checked weekly). Costs 2bp per side. Kill: -15% from core equity
peak -> cash 10 sessions, resume, peak resets to resume equity.

SATELLITE ($500 bankroll, one position): enter next open when (no position) AND
underlying close > MA200 AND RV21-rank < 0.40 AND modeled 75-DTE 0.5d call
<= $500/contract AND outside FOMC/CPI blackout (day before/of). Among qualifiers
pick highest 126d momentum. Exits: -50% premium stop, half off at +100%,
30-session time exit. Pricing identical to audited engine (BS, 1.08x RV63,
2.5% half-spread each way). Satellite full loss pre-accepted; no satellite kill.

Reported: A = core only. C = core + satellite on combined $2,100 base.
Benchmark: SPY buy & hold, 2bp entry cost.
"""
import copy, json, math, os, statistics
import engine
from engine import bs_call, strike_for_delta, rolling_ma, rolling_rv, rv_rank

SLIP = 0.0002
CORE0, SAT0 = 1600.0, 500.0

def week_ends(dates):
    """Indices of last trading day of each ISO week."""
    import datetime
    out = []
    for i, d in enumerate(dates):
        if i + 1 == len(dates): out.append(i); break
        a = datetime.date.fromisoformat(d); b = datetime.date.fromisoformat(dates[i + 1])
        if b.isocalendar()[:2] != a.isocalendar()[:2]: out.append(i)
    return out

def run_core(series, dates, i0, i1):
    syms = list(series.keys())
    ma = {s: rolling_ma(series[s]["c"], 200) for s in syms}
    we = set(week_ends(dates))
    cash, hold = CORE0, {}          # sym -> shares
    peak, kill_until, kills = CORE0, -1, []
    eq_curve, switches = [], 0
    pending = None                  # target set decided at week end, applied next open
    for i in range(i0, i1 + 1):
        # apply pending rebalance at today's open
        if pending is not None and i > kill_until:
            tgt = pending; pending = None
            cur = set(hold)
            if tgt != cur:
                switches += 1
                val = cash + sum(sh * series[s]["o"][i] for s, sh in hold.items())
                for s in list(hold):
                    cash += hold.pop(s) * series[s]["o"][i] * (1 - SLIP)
                if tgt:
                    per = (cash) / len(tgt)
                    for s in tgt:
                        px = series[s]["o"][i] * (1 + SLIP)
                        hold[s] = per / px
                        cash -= per
        equity = cash + sum(sh * series[s]["c"][i] for s, sh in hold.items())
        # kill check
        peak = max(peak, equity)
        if i > kill_until and equity <= peak * 0.85 and hold:
            for s in list(hold):
                cash += hold.pop(s) * series[s]["c"][i] * (1 - SLIP)
            equity = cash
            kills.append(dates[i]); kill_until = i + 10; peak = equity; pending = None
        eq_curve.append((dates[i], equity))
        # weekly decision at close
        if i in we and i > kill_until:
            qual = [s for s in syms if ma[s][i] is not None and series[s]["c"][i] > ma[s][i]
                    and i >= 126 and series[s]["c"][i - 126] > 0]
            mom = {s: series[s]["c"][i] / series[s]["c"][i - 126] - 1 for s in qual}
            top = sorted(qual, key=lambda s: -mom[s])[:2]
            pending = set(top)
        elif i in we and i <= kill_until:
            pending = None
    return dict(equity=eq_curve, kills=kills, switches=switches)

def run_satellite(series, dates, i0, i1, events):
    syms = list(series.keys())
    ma = {s: rolling_ma(series[s]["c"], 200) for s in syms}
    rv63 = {s: rolling_rv(series[s]["c"], 63) for s in syms}
    rv21 = {s: rolling_rv(series[s]["c"], 21) for s in syms}
    ivr = {s: rv_rank(rv21[s]) for s in syms}
    didx = {d: i for i, d in enumerate(dates)}
    ev_i = {didx[d] for d in events if d in didx}
    blocked = ev_i | {i - 1 for i in ev_i}
    cash, pos, trades, eq_curve = SAT0, None, [], []
    DTE, HS = 75, 0.025
    def mark(p, i):
        sig = 1.08 * (rv63[p["sym"]][i] or 0.3)
        T = max(p["exp"] - i, 0) / 252.0
        return bs_call(series[p["sym"]]["c"][i], p["K"], T, 0.04, sig)
    pending = None
    for i in range(i0, i1 + 1):
        if pending and pos is None:
            sym = pending; pending = None
            S = series[sym]["o"][i]
            sig = 1.08 * (rv63[sym][i - 1] or 0.3)
            T = DTE / 365
            K = strike_for_delta(S, T, 0.04, sig, 0.5)
            prem = bs_call(S, K, T, 0.04, sig)
            cost = prem * 100 * (1 + HS)
            if cost <= 500 and cost <= cash:
                cash -= cost
                pos = dict(sym=sym, K=K, exp=i + int(DTE * 252 / 365), prem=prem,
                           cost=cost, n=1, half=False, ei=i, recv=0.0)
        else:
            pending = None
        if pos:
            m = mark(pos, i)
            held = i - pos["ei"]
            reason = None
            if m <= 0.5 * pos["prem"]: reason = "stop"
            elif not pos["half"] and m >= 2 * pos["prem"]: reason = "target"  # 1 contract: full exit
            elif held >= 30: reason = "time"
            if reason:
                proceeds = pos["n"] * m * 100 * (1 - HS)
                cash += proceeds
                trades.append(dict(sym=pos["sym"], entry=dates[pos["ei"]], exit=dates[i],
                                   pnl=round(proceeds + pos["recv"] - pos["cost"], 2), reason=reason))
                pos = None
        equity = cash + (pos["n"] * mark(pos, i) * 100 if pos else 0)
        eq_curve.append((dates[i], equity))
        # signal at close for tomorrow
        if pos is None and pending is None and (i + 1) not in blocked and i + 1 <= i1:
            qual = []
            for s in syms:
                if ma[s][i] is None or series[s]["c"][i] <= ma[s][i]: continue
                if ivr[s][i] is None or ivr[s][i] >= 0.40: continue
                sig = 1.08 * (rv63[s][i] or 0.3)
                p_est = bs_call(series[s]["c"][i], strike_for_delta(series[s]["c"][i], 75/365, 0.04, sig, 0.5), 75/365, 0.04, sig)
                if p_est * 100 * 1.025 > 500: continue
                if i >= 126: qual.append((series[s]["c"][i] / series[s]["c"][i - 126] - 1, s))
            if qual:
                pending = max(qual)[1]
    return dict(equity=eq_curve, trades=trades)

def perf(eq, base):
    v = [x for _, x in eq]
    peak, mdd = v[0], 0.0
    for x in v:
        peak = max(peak, x); mdd = max(mdd, (peak - x) / peak)
    years = len(v) / 252
    cagr = (v[-1] / base) ** (1 / years) - 1 if v[-1] > 0 else -1
    rets = [v[i] / v[i - 1] - 1 for i in range(1, len(v)) if v[i - 1] > 0]
    downs = [r for r in rets if r < 0]
    dv = statistics.pstdev(downs) * math.sqrt(252) if len(downs) > 2 else None
    return dict(final=round(v[-1]), total=round(v[-1] / base - 1, 3), cagr=round(cagr, 3),
                max_dd=round(mdd, 3), sortino=round(cagr / dv, 2) if dv else None)

def spy_bh(series, dates, i0, i1, base):
    sh = base / (series["SPY"]["o"][i0] * (1 + SLIP))
    eq = [(dates[i], sh * series["SPY"]["c"][i]) for i in range(i0, i1 + 1)]
    return perf(eq, base), eq

def run_window(series, a, b, events):
    dates = series["SPY"]["dates"]
    didx = {d: i for i, d in enumerate(dates)}
    i0 = min(i for i, d in enumerate(dates) if d >= a); i0 = max(i0, 210)
    i1 = max(i for i, d in enumerate(dates) if d <= b)
    core = run_core(series, dates, i0, i1)
    sat = run_satellite(series, dates, i0, i1, events)
    comb = [(d, cv + sv) for (d, cv), (_, sv) in zip(core["equity"], sat["equity"])]
    bench, bench_eq = spy_bh(series, dates, i0, i1, 2100.0)
    return dict(
        A_core=perf(core["equity"], CORE0), core_kills=core["kills"], switches=core["switches"],
        SAT=perf(sat["equity"], SAT0), sat_trades=sat["trades"],
        C_combined=perf(comb, CORE0 + SAT0), SPY_bench=bench,
        curves=dict(C=comb, SPY=bench_eq, A=core["equity"]))

if __name__ == "__main__":
    import sys
    series = engine.load_all(engine.BASE_CONFIG)
    ev = engine.load_events()
    win = sys.argv[1] if len(sys.argv) > 1 else "build"
    a, b = ("2015-01-01", "2022-12-30") if win == "build" else ("2023-01-03", "2026-07-17")
    r = run_window(series, a, b, ev)
    print(f"== {win} {a}..{b} ==")
    print("A core-only :", r["A_core"], "kills:", r["core_kills"], "switches:", r["switches"])
    print("Satellite   :", r["SAT"], f"({len(r['sat_trades'])} trades)")
    for t in r["sat_trades"]: print("   ", t)
    print("C combined  :", r["C_combined"])
    print("SPY buy&hold:", r["SPY_bench"])
    json.dump({k: v for k, v in r.items() if k != "curves"},
              open(os.path.join(os.path.dirname(__file__), "..", "charts", f"planc_{win}.json"), "w"), indent=1, default=str)
    # save curves for charting
    json.dump(r["curves"], open(os.path.join(os.path.dirname(__file__), "..", "charts", f"planc_curves_{win}.json"), "w"))
