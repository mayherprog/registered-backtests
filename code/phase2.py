"""Phase 2: constrained alternative search.
Guardrails (non-negotiable, from the project spec):
  - Optimize on BUILD = 2015-01-01..2022-12-30 ONLY.
  - VALIDATION = 2023-01-03..2026-07-17, untouched by selection.
  - Max 24 candidates, every one logged (incl. discards) in ../candidates.md.
  - Complexity penalty: a candidate that ADDS a structural rule (new mechanism)
    must beat a simpler candidate's build Sortino by +0.10 absolute per added
    rule, else the simpler one wins. Parameter changes to existing rules add 0.
  - Entries searched LAST, never more than 2 indicators per trigger.
  - Champion (BASE plan) is replaced only if finalist beats it on VALIDATION
    risk-adjusted return AND max drawdown.
Walk-forward: build split into 4 two-year folds; finalist must beat BASE on
avg-R (EV lens) in >= 3 of 4 folds to survive.
"""
import copy, json, math, os, statistics
import engine

BUILD = ("2015-01-01", "2022-12-30")
VALID = ("2023-01-03", "2026-07-17")
FOLDS = [("2015-01-01","2016-12-30"),("2017-01-03","2018-12-31"),
         ("2019-01-02","2020-12-31"),("2021-01-04","2022-12-30")]

# (name, cfg mods, added_structural_rules, category, rationale)
CANDIDATES = [
 ("C01 stop -60",            {"stop_frac":0.60}, 0, "risk", "sensitivity said tighter stops hurt; test looser"),
 ("C02 no-invalidation",     {"use_invalidation":False}, 0, "risk", "MA-touch invalidation whipsaws; premium stop only"),
 ("C03 vol-scaled size",     {"vol_size_ref":0.20}, 1, "risk", "shrink size when RV63 high; buys premium cheaper risk"),
 ("C04 concurrency 2 + sector 1", {"max_positions":2,"max_per_sector":1}, 0, "risk", "cut correlated equity beta stacking"),
 ("C05 dd throttle 15%",     {"dd_throttle":0.15}, 1, "risk", "halve size in drawdown, soften kill spiral"),
 ("C06 extended blackout",   {"__blackout2":True}, 1, "risk", "blackout helped; extend to 2 days pre-event"),
 ("C07 stop -60 + no-inval", {"stop_frac":0.60,"use_invalidation":False}, 0, "risk", "combine the two loosening changes"),
 ("C08 take +75%",           {"profit_take":0.75}, 0, "exit", "bank winners earlier, raise win rate"),
 ("C09 take +150%",          {"profit_take":1.50}, 0, "exit", "let winners run further"),
 ("C10 time stop 25",        {"max_hold":25}, 0, "exit", "cut theta bleed on dead trades"),
 ("C11 breakeven trail",     {"be_trail":True}, 1, "exit", "after +50 pct never give it all back"),
 ("C12 no-inval + take +150",{"use_invalidation":False,"profit_take":1.50}, 0, "exit", "loosen exits both directions"),
 ("C13 reclaim buffer 1%",   {"entry_buffer":0.01}, 0, "entry", "avoid entries sitting on the MA"),
 ("C14 reclaim hold 3",      {"reclaim_hold":3}, 0, "entry", "stronger confirmation"),
 ("C15 trend filter MA200",  {"trend_filter":200}, 1, "entry", "only long above long-term trend (2nd indicator)"),
 ("C16 higher-low only",     {"triggers":dict(reclaim50=False,higher_low=True,xbi_breakout=False,xbi_support=False)}, 0, "entry", "keep only least-bad trigger"),
 ("C17 breakout 55d",        {"breakout_len":55}, 0, "entry", "rarer, stronger XBI breakouts"),
 ("C18 C02+C15",             {"use_invalidation":False,"trend_filter":200}, 1, "combo", "best risk + best entry filter"),
 ("C19 C02+C03+C15",         {"use_invalidation":False,"vol_size_ref":0.20,"trend_filter":200}, 2, "combo", "add vol sizing"),
 ("C20 C02+C15+take150",     {"use_invalidation":False,"trend_filter":200,"profit_take":1.50}, 1, "combo", "and let winners run"),
]

def sortino(eq_curve):
    eq = [v for _, v in eq_curve]
    rets = [eq[i]/eq[i-1]-1 for i in range(1, len(eq)) if eq[i-1] > 0]
    if len(rets) < 20: return None
    years = len(eq)/252
    cagr = (eq[-1]/eq[0])**(1/years)-1 if eq[-1] > 0 else -1
    downs = [r for r in rets if r < 0]
    dv = statistics.pstdev(downs)*math.sqrt(252) if len(downs) > 2 else None
    if not dv: return None
    return cagr/dv

def evaluate(mods, window, series, ev):
    cfg = copy.deepcopy(engine.BASE_CONFIG)
    blackout2 = mods.pop("__blackout2", False) if "__blackout2" in mods else False
    for k, v in mods.items(): cfg[k] = v
    ev_use = ev
    if blackout2:
        # widen: add the day before the day-before (2 trading days pre-event)
        dates = series["SPY"]["dates"]; didx = {d:i for i,d in enumerate(dates)}
        extra = set()
        for d in ev:
            if d in didx and didx[d] >= 2: extra.add(dates[didx[d]-2])
        ev_use = ev | extra
    r_pl = engine.run_backtest(series, cfg, start_date=window[0], end_date=window[1], events=ev_use)
    s = engine.stats(r_pl, cfg["bankroll"], cfg["stop_frac"])
    cfg2 = copy.deepcopy(cfg); cfg2["kill_mode"]="off"; cfg2["infinite_bankroll"]=True
    r_ev = engine.run_backtest(series, cfg2, start_date=window[0], end_date=window[1], events=ev_use)
    tr = r_ev["trades"]
    rs = [t["pnl"]/(cfg["stop_frac"]*t["cost"]) for t in tr if t["cost"]>0]
    return dict(final=s["final"], dd=s["max_dd"], kills=s["kill_trips"],
                sortino=round(sortino(r_pl["equity"]) or -9, 3),
                n=len(tr), avgR=round(sum(rs)/len(rs), 3) if rs else None,
                totpnl=round(sum(t["pnl"] for t in tr)))

def main():
    series = engine.load_all(engine.BASE_CONFIG)
    ev = engine.load_events()
    results = []
    base_b = evaluate({}, BUILD, series, ev)
    print(f"BASE build: {base_b}")
    for name, mods, added, cat, why in CANDIDATES:
        r = evaluate(dict(mods), BUILD, series, ev)
        results.append(dict(name=name, cat=cat, added_rules=added, why=why, build=r))
        print(f"{name:28s} [{cat}] final=${r['final']:>6.0f} dd={r['dd']:.0%} srt={r['sortino']:+.2f} "
              f"avgR={r['avgR']:+.3f} pnl={r['totpnl']:+7d} n={r['n']}")
    json.dump(dict(base=base_b, candidates=results),
              open(os.path.join(os.path.dirname(__file__), "..", "charts", "phase2_build.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
