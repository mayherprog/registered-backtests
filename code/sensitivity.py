"""One-rule-at-a-time sensitivity, 2015-01-01..2026-07-17.
Two lenses per variant:
  EV lens  — kill off + infinite bankroll, constant sizing: avg R per trade, total pnl.
             Isolates per-trade economics from bankroll death.
  Plan lens — full plan rules with $2,100: final equity, max DD, kill trips.
vol_mult and spread rows measure model/pricing uncertainty, not plan rules."""
import copy, json, os
import engine

START, END = "2015-01-01", "2026-07-17"

def run(cfg_mods, series, ev):
    base = copy.deepcopy(engine.BASE_CONFIG)
    for k, v in cfg_mods.items():
        base[k] = v
    ev_cfg = copy.deepcopy(base); ev_cfg["kill_mode"] = "off"; ev_cfg["infinite_bankroll"] = True
    r_ev = engine.run_backtest(series, ev_cfg, start_date=START, end_date=END, events=ev)
    r_pl = engine.run_backtest(series, base, start_date=START, end_date=END, events=ev)
    tr = r_ev["trades"]
    rs = [t["pnl"] / (base["stop_frac"] * t["cost"]) for t in tr if t["cost"] > 0]
    s_pl = engine.stats(r_pl, base["bankroll"], base["stop_frac"])
    return dict(
        n=len(tr),
        avg_R=round(sum(rs) / len(rs), 3) if rs else None,
        total_pnl=round(sum(t["pnl"] for t in tr)),
        win=round(sum(1 for t in tr if t["pnl"] > 0) / len(tr), 3) if tr else None,
        plan_final=s_pl["final"], plan_dd=s_pl["max_dd"], plan_kills=s_pl["kill_trips"],
    )

VARIANTS = [
    ("BASE (plan as written)", {}),
    ("stop -35%", {"stop_frac": 0.35}),
    ("stop -40%", {"stop_frac": 0.40}),
    ("stop -60%", {"stop_frac": 0.60}),
    ("no invalidation exit (stop only)", {"__no_inval": True}),
    ("concurrency 2", {"max_positions": 2}),
    ("concurrency 4", {"max_positions": 4}),
    ("fixed $500 size", {"fixed_size": 500.0}),
    ("blackout off", {"blackout": False}),
    ("IV filter off", {"iv_filter": False}),
    ("IV filter skip (not halve)", {"iv_action": "skip"}),
    ("[pricing] vol_mult 0.95", {"vol_mult": 0.95}),
    ("[pricing] vol_mult 1.25", {"vol_mult": 1.25}),
    ("[cost] zero spread", {"spread_frac": 0.0}),
    ("[cost] 5% half-spread", {"spread_frac": 0.05}),
]

def main():
    series = engine.load_all(engine.BASE_CONFIG)
    ev = engine.load_events()
    out = []
    for name, mods in VARIANTS:
        mods = dict(mods)
        no_inval = mods.pop("__no_inval", False)
        if no_inval:
            # disable invalidation by patching: run with inval None via monkey config
            # simplest faithful switch: set invalidation levels to 0 by post-processing signals
            import engine as e
            orig = e.build_signals
            def patched(series_, cfg_):
                sigs = orig(series_, cfg_)
                return {s: [(t, tr, None) for t, tr, _ in lst] for s, lst in sigs.items()}
            e.build_signals = patched
            try:
                r = run(mods, series, ev)
            finally:
                e.build_signals = orig
        else:
            r = run(mods, series, ev)
        r["variant"] = name
        out.append(r)
        print(f"{name:34s} n={r['n']:4d} avgR={r['avg_R']:+.3f} totPnl={r['total_pnl']:+7d} "
              f"win={r['win']:.3f} | plan: final=${r['plan_final']:>6.0f} dd={r['plan_dd']:.1%} kills={r['plan_kills']}")
    json.dump(out, open(os.path.join(os.path.dirname(__file__), "..", "charts", "sensitivity.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
