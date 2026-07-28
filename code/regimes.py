"""Regime tests: fresh $2,100 bankroll per window, plan rules (kill_mode=plan).
Also runs a kill-off diagnostic per regime to characterize the rules independent
of the kill switch. Saves equity curve PNGs to ../charts/."""
import copy, json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import engine

REGIMES = [
    ("2015-2017_chop_grind", "2015-01-01", "2017-12-29"),
    ("2018_vol_spike",       "2018-01-01", "2018-12-31"),
    ("2020_crash_recovery",  "2020-01-01", "2020-12-31"),
    ("2022_bear",            "2022-01-03", "2022-12-30"),
    ("2023-2024_recovery",   "2023-01-03", "2024-12-31"),
    ("2025-2026_momentum",   "2025-01-02", "2026-07-17"),
]

def days_to_kill(res):
    if not res["kill_trips"]: return None
    d0 = res["equity"][0][0]
    dk = res["kill_trips"][0]
    return sum(1 for d, _ in res["equity"] if d0 <= d <= dk)

def main():
    cfg = copy.deepcopy(engine.BASE_CONFIG)
    series = engine.load_all(cfg)
    ev = engine.load_events()
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "charts"), exist_ok=True)
    rows = []
    for name, a, b in REGIMES:
        r_plan = engine.run_backtest(series, cfg, start_date=a, end_date=b, events=ev)
        s_plan = engine.stats(r_plan, cfg["bankroll"], cfg["stop_frac"])
        cfg_off = copy.deepcopy(cfg); cfg_off["kill_mode"] = "off"
        r_off = engine.run_backtest(series, cfg_off, start_date=a, end_date=b, events=ev)
        s_off = engine.stats(r_off, cfg["bankroll"], cfg["stop_frac"])
        rows.append(dict(regime=name, plan=s_plan, kill_off=s_off,
                         sessions_to_first_kill=days_to_kill(r_plan)))
        # chart
        fig, ax = plt.subplots(figsize=(9, 4.2))
        d1 = [d for d, _ in r_plan["equity"]]; v1 = [v for _, v in r_plan["equity"]]
        v2 = [v for _, v in r_off["equity"]]
        ax.plot(range(len(v1)), v1, label="plan rules (kill switch live)", lw=1.6)
        ax.plot(range(len(v2)), v2, label="kill switch off (diagnostic)", lw=1.0, alpha=0.7)
        ax.axhline(2100, color="gray", lw=0.6, ls="--")
        ax.axhline(1470, color="red", lw=0.6, ls="--", label="-30% kill floor")
        step = max(1, len(d1) // 8)
        ax.set_xticks(range(0, len(d1), step))
        ax.set_xticklabels([d1[i] for i in range(0, len(d1), step)], rotation=30, fontsize=7)
        for k in r_plan["kill_trips"]:
            ax.axvline(d1.index(k), color="red", alpha=0.4, lw=0.8)
        ax.set_title(f"Engine 1 equity, {name} (fresh $2,100)")
        ax.set_ylabel("$"); ax.legend(fontsize=8); fig.tight_layout()
        fig.savefig(os.path.join(os.path.dirname(__file__), "..", "charts", f"equity_{name}.png"), dpi=110)
        plt.close(fig)
    out = os.path.join(os.path.dirname(__file__), "..", "charts", "regime_stats.json")
    json.dump(rows, open(out, "w"), indent=1, default=str)
    for r in rows:
        p, o = r["plan"], r["kill_off"]
        print(f"{r['regime']:24s} plan: ret={p['total_return']:+.1%} dd={p['max_dd']:.1%} "
              f"n={p['trades']} win={p['win_rate']} R={p['avg_R']} kills={p['kill_trips']} "
              f"t2k={r['sessions_to_first_kill']} | killoff: ret={o['total_return']:+.1%} "
              f"dd={o['max_dd']:.1%} n={o['trades']}")

if __name__ == "__main__":
    main()
