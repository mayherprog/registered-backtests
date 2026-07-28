"""12 registered strategies (strategies_registration.md). No parameter differs from the
registration doc. Execution conventions:
  monthly/weekly: decide at bar t close, execute at bar t+1 open.
  daily S3/S4/S5/S6: enter/exit at the signal bar's close (market-on-close convention,
  as published; noted in report).
Costs: 2bp per side on every traded notional. Cash: SHY monthly total return for monthly
strategies; 0 for daily/weekly strategies (registered, conservative).
"""
import bisect, csv, math, os, statistics, json

D = os.path.join(os.path.dirname(__file__), "..", "data")
COST = 0.0002
BUILD = ("2015-01-01", "2022-12-30")
VALID = ("2023-01-03", "2026-07-17")
FOLDS = [("2015-01-01","2016-12-31"),("2017-01-01","2018-12-31"),
         ("2019-01-01","2020-12-31"),("2021-01-01","2022-12-31")]

def load(fn):
    rows = list(csv.DictReader(open(os.path.join(D, fn))))
    return dict(d=[r["date"] for r in rows], o=[float(r["open"]) for r in rows],
                h=[float(r["high"]) for r in rows], l=[float(r["low"]) for r in rows],
                c=[float(r["close"]) for r in rows])

def resample(s, mode):
    """daily -> weekly(fri) or monthly(last trading day). Keeps (date, open-of-period, close)."""
    out = dict(d=[], o=[], c=[], h=[], l=[])
    cur = None
    for i, dt in enumerate(s["d"]):
        key = dt[:7] if mode == "M" else _week_key(dt)
        if key != cur:
            if cur is not None:
                out["d"].append(prev_dt); out["o"].append(po); out["c"].append(pc)
                out["h"].append(ph); out["l"].append(pl)
            cur = key; po = s["o"][i]; ph = s["h"][i]; pl = s["l"][i]
        ph = max(ph, s["h"][i]); pl = min(pl, s["l"][i])
        pc = s["c"][i]; prev_dt = dt
    out["d"].append(prev_dt); out["o"].append(po); out["c"].append(pc)
    out["h"].append(ph); out["l"].append(pl)
    return out

def _week_key(dt):
    import datetime
    d = datetime.date.fromisoformat(dt)
    y, w, _ = d.isocalendar()
    return f"{y}-{w:02d}"

def downside_dev(rets, npy, mar=0.0):
    """Annualized downside deviation: root-mean-square shortfall below MAR, averaged
    over ALL periods (periods at or above MAR contribute zero). This is the standard
    denominator of the Sortino ratio.

    Until 2026-07-28 this was statistics.pstdev of only the negative returns, which
    measures dispersion AMONG losses rather than the magnitude of loss, is smaller in
    general, and therefore inflated every Sortino in this project. It was also
    unstable when few negative periods existed, which is exactly the case in a
    two-year monthly fold (~24 bars)."""
    if len(rets) < 3: return None
    short = [min(r - mar, 0.0) for r in rets]
    dd = math.sqrt(sum(x * x for x in short) / len(short))
    return dd * math.sqrt(npy) if dd > 0 else None


def perf(eq, npy):
    """Performance of an equity curve sampled npy times per year.

    npy is REQUIRED and must be the strategy's native bar frequency. It was
    previously inferred from len(eq), which silently misread every two-year fold:
    ~504 daily bars fell under the >600 threshold and were annualized as weekly,
    reporting 9.7 years for a 2-year window. The inference happened to be right on
    the full 8-year build window and wrong on exactly the fold slices that the
    3-of-4 robustness gate depends on."""
    v = [x for _, x in eq]
    if not v or v[0] <= 0: return None
    peak, mdd = v[0], 0.0
    for x in v:
        peak = max(peak, x); mdd = max(mdd, (peak - x) / peak if peak > 0 else 0)
    years = len(v) / npy
    cagr = (v[-1] / v[0]) ** (1 / years) - 1 if years > 0 and v[-1] > 0 else -1
    rets = [v[i] / v[i-1] - 1 for i in range(1, len(v)) if v[i-1] > 0]
    dv = downside_dev(rets, npy)
    return dict(cagr=round(cagr, 4), max_dd=round(mdd, 4),
                sortino=round(cagr / dv, 2) if dv else None, final_mult=round(v[-1] / v[0], 3))


def resample_eq(eq, npy):
    """Downsample a daily equity curve to weekly or monthly last observations.

    Downside deviation scales with sampling frequency, so a monthly strategy
    measured against a daily benchmark is not a like-for-like comparison. The
    benchmark is resampled to each strategy's own frequency before comparing."""
    if npy >= 252: return eq
    keyfn = (lambda d: d[:7]) if npy <= 12 else _week_key
    out, cur, last = [], None, None
    for d, v in eq:
        k = keyfn(d)
        if cur is None: cur = k
        if k != cur:
            out.append(last); cur = k
        last = (d, v)
    if last: out.append(last)
    return out

def slice_eq(eq, a, b): return [(d, v) for d, v in eq if a <= d <= b]


def slice_exp(eq, exp, a, b):
    """Exposure values for the bars slice_eq would keep. eq and exp are parallel."""
    return [x for (d, _), x in zip(eq, exp) if a <= d <= b]


def _asof(dates, vals, d):
    """Last value at or before date d (last observation carried forward)."""
    i = bisect.bisect_right(dates, d) - 1
    return vals[i] if i >= 0 else None


def matched_bench_eq(eq_dates, e, dl, ml, use_shy):
    """Gate 2 benchmark: a constant-exposure portfolio holding e in SPY and (1-e) in
    the strategy's own registered cash asset, sampled on exactly the strategy's bar
    dates so that the annualization and bar count match. See gate2_registration.md."""
    sd, sc = dl["spy"]["d"], dl["spy"]["c"]
    hd, hc = (ml["shy"]["d"], ml["shy"]["c"]) if use_shy else (None, None)
    out, v = [], 1.0
    prev_s = prev_h = None
    for k, d in enumerate(eq_dates):
        s = _asof(sd, sc, d)
        h = _asof(hd, hc, d) if use_shy else None
        if k > 0:
            rs = (s / prev_s - 1) if (s and prev_s) else 0.0
            rc = (h / prev_h - 1) if (use_shy and h and prev_h) else 0.0
            v *= (1 + e * rs + (1 - e) * rc)
        out.append((d, v))
        prev_s, prev_h = s, h
    return out

def ret_series(bars):
    """close-to-close returns keyed by bar index."""
    return [None] + [bars["c"][i] / bars["c"][i-1] - 1 for i in range(1, len(bars["c"]))]

# ---------- generic engines ----------
def run_switcher(bars_map, choose, start, end, cash_ret=None, warmup=13):
    """Monthly/weekly single-holding engine. choose(i-1) -> symbol key or 'CASH', decided
    from data through bar i-1's close, and the position then earns the close(i-1) ->
    close(i) return. That is market-on-close execution at the decision bar: the decision
    and the fill happen at the same close, with no lookahead, but no overnight gap either.
    (The docstring previously claimed execution at bar i+1's open, which the code has
    never done. Corrected 2026-07-28; the code is unchanged.)
    All bars_map series must share the calendar of bars_map['_cal'] (list of dates)."""
    cal = bars_map["_cal"]
    rets = {k: ret_series(v) for k, v in bars_map.items() if k != "_cal"}
    eq, exp, v = [], [], 1.0
    holding = "CASH"
    for i in range(warmup, len(cal)):
        dt = cal[i]
        if dt < start:
            holding = choose(i - 1) or "CASH"
            continue
        if dt > end: break
        # return for this bar from holding decided at i-1
        tgt = choose(i - 1) or "CASH"
        if tgt != holding:
            v *= (1 - 2 * COST)   # sell old, buy new (round trip on switch)
            holding = tgt
        if holding == "CASH":
            r = cash_ret(i) if cash_ret else 0.0
        else:
            r = rets[holding][i] or 0.0
        v *= (1 + r)
        eq.append((dt, v))
        exp.append(0.0 if holding == "CASH" else 1.0)   # Gate 2 capital exposure
    return eq, exp

def run_flag_daily(bars, in_market, start, end):
    """Daily engine: in_market(i) decided using data through close of bar i; position holds
    the close(i)->close(i+1) return. Entry/exit at closes with cost per switch."""
    eq, exp, v, pos = [], [], 1.0, False
    for i in range(220, len(bars["d"]) - 1):
        dt = bars["d"][i]
        if dt < start: pos = in_market(i); continue
        if dt > end: break
        tgt = in_market(i)
        if tgt != pos:
            v *= (1 - COST)
            pos = tgt
        if pos:
            v *= bars["c"][i + 1] / bars["c"][i]
        eq.append((bars["d"][i + 1], v))
        exp.append(1.0 if pos else 0.0)   # Gate 2 capital exposure
    return eq, exp

# ---------- indicators ----------
def sma(vals, n, i):
    if i + 1 < n: return None
    return sum(vals[i - n + 1:i + 1]) / n

def rsi2(c, i):
    if i < 3: return None
    gains = losses = 0.0
    # Wilder RSI(2): use simple 2-period average of up/down moves (standard short RSI approx)
    for k in (i - 1, i):
        ch = c[k] - c[k - 1]
        if ch > 0: gains += ch
        else: losses -= ch
    if losses == 0: return 100.0
    rs = (gains / 2) / (losses / 2)
    return 100 - 100 / (1 + rs)

def r_n(c, i, n):  # n-bar return
    if i < n or c[i - n] <= 0: return None
    return c[i] / c[i - n] - 1

# ---------- strategy builders (each returns equity curve for [start, end]) ----------
def month_cal(*series_list):
    """common monthly calendar = intersection by YYYY-MM, using the LAST bar of each month."""
    keyed = []
    for s in series_list:
        m = {}
        for i, dt in enumerate(s["d"]): m[dt[:7]] = i
        keyed.append(m)
    common = sorted(set.intersection(*[set(k) for k in keyed]))
    return common, keyed

def build_monthly_map(specs):
    """specs: dict name->bars. Aligns all to common months; returns bars_map for run_switcher."""
    names = list(specs)
    common, keyed = month_cal(*[specs[n] for n in names])
    out = {"_cal": []}
    for n in names: out[n] = dict(c=[], d=[])
    for mth in common:
        out["_cal"].append(max(specs[names[0]]["d"][keyed[0][mth]],
                               *[specs[n]["d"][keyed[j][mth]] for j, n in enumerate(names)]))
        for j, n in enumerate(names):
            out[n]["c"].append(specs[n]["c"][keyed[j][mth]])
    return out

def s1_gem(dl, ml, start, end):
    m = build_monthly_map(dict(SPY=dl["spy_m"], EFA=ml["efa"], SHY=ml["shy"], TLT=dl["tlt_m"]))
    shy_r = ret_series(m["SHY"])
    def choose(i):
        rs, re_, rb = r_n(m["SPY"]["c"], i, 12), r_n(m["EFA"]["c"], i, 12), r_n(m["SHY"]["c"], i, 12)
        if None in (rs, re_, rb): return "CASH"
        if max(rs, re_) > rb: return "SPY" if rs >= re_ else "EFA"
        return "TLT"
    return run_switcher(m, choose, start, end, cash_ret=lambda i: shy_r[i] or 0.0)

def s2_gtaa(dl, ml, start, end):
    specs = dict(SPY=dl["spy_m"], EFA=ml["efa"], TLT=dl["tlt_m"], GLD=ml["gld"], VNQ=ml["vnq"], SHY=ml["shy"])
    m = build_monthly_map(specs)
    rets = {k: ret_series(v) for k, v in m.items() if k != "_cal"}
    eq, exp, v = [], [], 1.0
    prev = {k: False for k in ("SPY","EFA","TLT","GLD","VNQ")}
    for i in range(11, len(m["_cal"])):
        dt = m["_cal"][i]
        if dt > end: break
        r_total = 0.0
        n_on = 0
        for k in prev:
            on = sma(m[k]["c"], 10, i - 1) is not None and m[k]["c"][i - 1] > sma(m[k]["c"], 10, i - 1)
            cost = COST * 2 if on != prev[k] else 0.0
            sleeve_r = (rets[k][i] or 0.0) if on else (rets["SHY"][i] or 0.0)
            r_total += 0.2 * (sleeve_r - cost)
            prev[k] = on
            n_on += 1 if on else 0
        v *= (1 + r_total)
        if dt >= start:
            eq.append((dt, v))
            exp.append(0.2 * n_on)   # Gate 2: fraction of the 5 sleeves risk-on
    return eq, exp

def s3_rsi2(dl, ml, start, end):
    b = dl["spy"]
    c = b["c"]
    state = {"pos": False}
    def in_mkt(i):
        m200 = sma(c, 200, i); m5 = sma(c, 5, i); r = rsi2(c, i)
        if None in (m200, m5, r): return False
        if not state["pos"]:
            if r < 5 and c[i] > m200: state["pos"] = True
        else:
            if c[i] > m5: state["pos"] = False
        return state["pos"]
    return run_flag_daily(b, in_mkt, start, end)

def s4_ibs(dl, ml, start, end):
    b = dl["qqq"]
    state = {"pos": False}
    def in_mkt(i):
        rng = b["h"][i] - b["l"][i]
        ibs = (b["c"][i] - b["l"][i]) / rng if rng > 0 else 0.5
        m200 = sma(b["c"], 200, i)
        if m200 is None: return False
        if not state["pos"]:
            if ibs < 0.20 and b["c"][i] > m200: state["pos"] = True
        else:
            if ibs > 0.80: state["pos"] = False
        return state["pos"]
    return run_flag_daily(b, in_mkt, start, end)

def s5_tom(dl, ml, start, end):
    b = dl["spy"]; d = b["d"]
    month_of = [x[:7] for x in d]
    in_win = [False] * len(d)
    # find month boundaries
    idx_by_month = {}
    for i, mth in enumerate(month_of): idx_by_month.setdefault(mth, []).append(i)
    months = sorted(idx_by_month)
    for mi, mth in enumerate(months):
        idxs = idx_by_month[mth]
        if len(idxs) >= 4:
            for i in idxs[-4:]: in_win[i] = True   # last 4 trading days
        for i in idxs[:3]: in_win[i] = True        # first 3 trading days
    return run_flag_daily(b, lambda i: in_win[i], start, end)

def s6_halloween(dl, ml, start, end):
    b = dl["spy"]
    def in_mkt(i):
        mth = int(b["d"][i][5:7])
        return mth >= 11 or mth <= 4
    return run_flag_daily(b, in_mkt, start, end)

def s7_adm(dl, ml, start, end):
    m = build_monthly_map(dict(SPY=dl["spy_m"], SCZ=ml["scz"], TLT=dl["tlt_m"], SHY=ml["shy"]))
    shy_r = ret_series(m["SHY"])
    def choose(i):
        def score(c):
            rs = [r_n(c, i, n) for n in (1, 3, 6)]
            return None if None in rs else sum(rs) / 3
        a, b2 = score(m["SPY"]["c"]), score(m["SCZ"]["c"])
        if None in (a, b2): return "CASH"
        if max(a, b2) > 0: return "SPY" if a >= b2 else "SCZ"
        return "TLT"
    return run_switcher(m, choose, start, end, cash_ret=lambda i: shy_r[i] or 0.0)

def s8_vaa(dl, ml, start, end):
    m = build_monthly_map(dict(SPY=dl["spy_m"], EFA=ml["efa"], EEM=ml["eem"], AGG=ml["agg"],
                               SHY=ml["shy"], IEF=ml["ief"], LQD=ml["lqd"]))
    shy_r = ret_series(m["SHY"])
    def mom(c, i):
        rs = [r_n(c, i, n) for n in (1, 3, 6, 12)]
        if None in rs: return None
        return 12 * rs[0] + 4 * rs[1] + 2 * rs[2] + 1 * rs[3]
    OFF, DEF = ("SPY", "EFA", "EEM", "AGG"), ("SHY", "IEF", "LQD")
    def choose(i):
        offs = {k: mom(m[k]["c"], i) for k in OFF}
        defs = {k: mom(m[k]["c"], i) for k in DEF}
        if any(v is None for v in offs.values()) or any(v is None for v in defs.values()):
            return "CASH"
        if all(v > 0 for v in offs.values()):
            return max(offs, key=offs.get)
        return max(defs, key=defs.get)
    return run_switcher(m, choose, start, end, cash_ret=lambda i: shy_r[i] or 0.0)

def s9_gayed(dl, ml, start, end):
    spy_w, sso_w = dl["spy_w"], dl["wk"]["sso"]
    m = build_weekly_map(dict(SPY=spy_w, SSO=sso_w))
    def choose(i):
        s10 = sma(m["SPY"]["c"], 40, i)
        if s10 is None: return "CASH"
        return "SSO" if m["SPY"]["c"][i] > s10 else "CASH"
    return run_switcher(m, choose, start, end, warmup=41)

def build_weekly_map(specs):
    names = list(specs)
    keyed = []
    for n in names:
        k = {}
        for i, dt in enumerate(specs[n]["d"]): k[_week_key(dt)] = i
        keyed.append(k)
    common = sorted(set.intersection(*[set(k) for k in keyed]))
    out = {"_cal": []}
    for n in names: out[n] = dict(c=[])
    for wk in common:
        out["_cal"].append(max(specs[n]["d"][keyed[j][wk]] for j, n in enumerate(names)))
        for j, n in enumerate(names):
            out[n]["c"].append(specs[n]["c"][keyed[j][wk]])
    return out

def s10_hfea(dl, ml, start, end):
    m = build_weekly_map(dict(UPRO=dl["wk"]["upro"], TMF=dl["wk"]["tmf"]))
    ru, rt = ret_series(m["UPRO"]), ret_series(m["TMF"])
    eq, exp, v = [], [], 1.0
    wu = 0.55
    k = 0
    for i in range(1, len(m["_cal"])):
        dt = m["_cal"][i]
        if dt > end: break
        r = wu * (ru[i] or 0) + (1 - wu) * (rt[i] or 0)
        v *= (1 + r)
        # drift weights, rebalance every 13 weeks
        vu = wu * (1 + (ru[i] or 0)); vt = (1 - wu) * (1 + (rt[i] or 0))
        wu = vu / (vu + vt)
        k += 1
        if k % 13 == 0:
            v *= (1 - COST * 2 * abs(wu - 0.55))
            wu = 0.55
        if dt >= start:
            eq.append((dt, v))
            exp.append(1.0)   # Gate 2: always fully invested by registration
    return eq, exp

def s11_volmanaged(dl, ml, start, end):
    b = dl["spy"]; c = b["c"]
    import datetime
    eq, exp, v = [], [], 1.0
    w = 0.0
    for i in range(23, len(c) - 1):
        dt = b["d"][i]
        if dt > end: break
        # month-end: recompute weight
        if i + 1 < len(c) and b["d"][i + 1][:7] != dt[:7]:
            rets = [math.log(c[k] / c[k - 1]) for k in range(i - 20, i + 1)]
            mu = sum(rets) / len(rets)
            rv = math.sqrt(sum((x - mu) ** 2 for x in rets) / (len(rets) - 1)) * math.sqrt(252)
            new_w = min(1.0, 0.15 / rv) if rv > 0 else 1.0
            v *= (1 - COST * abs(new_w - w))
            w = new_w
        r = c[i + 1] / c[i] - 1
        v *= (1 + w * r)
        if b["d"][i + 1] >= start:
            eq.append((b["d"][i + 1], v))
            exp.append(min(1.0, w))   # Gate 2: vol-target weight actually applied
    return eq, exp

def s12_btc(dl, ml, start, end):
    btc = dl["wk"]["btc"]
    m = {"_cal": btc["d"], "BTC": dict(c=btc["c"])}
    def choose(i):
        s40 = sma(btc["c"], 40, i)
        if s40 is None: return "CASH"
        return "BTC" if btc["c"][i] > s40 else "CASH"
    return run_switcher(m, choose, start, end, warmup=41)

def spy_bench(dl, start, end):
    b = dl["spy"]
    eq = []
    base = None
    for i, dt in enumerate(b["d"]):
        if dt < start or dt > end: continue
        if base is None: base = b["c"][i]
        eq.append((dt, b["c"][i] / base))
    return eq

STRATS = [
    ("S1 GEM", s1_gem), ("S2 GTAA-5", s2_gtaa), ("S3 RSI-2 SPY", s3_rsi2),
    ("S4 IBS QQQ", s4_ibs), ("S5 Turn-of-month", s5_tom), ("S6 Halloween", s6_halloween),
    ("S7 Accel dual mom", s7_adm), ("S8 VAA-G4", s8_vaa), ("S9 Gayed SSO 40w", s9_gayed),
    ("S10 HFEA", s10_hfea), ("S11 Vol-managed SPY", s11_volmanaged), ("S12 BTC 40w trend", s12_btc),
]

# Native bar frequency of each strategy's equity curve, per the registration doc.
# Passed explicitly to perf() rather than inferred from array length.
FREQ = {
    "S1 GEM": 12, "S2 GTAA-5": 12, "S7 Accel dual mom": 12, "S8 VAA-G4": 12,
    "S9 Gayed SSO 40w": 52, "S10 HFEA": 52, "S12 BTC 40w trend": 52,
    "S3 RSI-2 SPY": 252, "S4 IBS QQQ": 252, "S5 Turn-of-month": 252,
    "S6 Halloween": 252, "S11 Vol-managed SPY": 252,
}

def load_all_data():
    dl = dict(spy=load("spy.csv"), qqq=load("qqq.csv"))
    dl["spy_m"] = resample(dl["spy"], "M")
    dl["spy_w"] = resample(dl["spy"], "W")
    dl["wk"] = {s: load(f"{s}_w.csv") for s in ("sso", "upro", "tmf", "tlt", "btc")}
    # TLT monthly from weekly (last week of month) - registered approximation
    tlt_m = dict(d=[], o=[], c=[], h=[], l=[])
    w = dl["wk"]["tlt"]
    for i, dt in enumerate(w["d"]):
        if i + 1 == len(w["d"]) or w["d"][i + 1][:7] != dt[:7]:
            tlt_m["d"].append(dt); tlt_m["c"].append(w["c"][i]); tlt_m["o"].append(w["o"][i])
            tlt_m["h"].append(w["h"][i]); tlt_m["l"].append(w["l"][i])
    dl["tlt_m"] = tlt_m
    ml = {s: load(f"{s}_m.csv") for s in ("efa", "gld", "vnq", "scz", "eem", "agg", "ief", "lqd", "shy")}
    return dl, ml

def evaluate(window):
    dl, ml = load_all_data()
    a, b = window
    bench_d = spy_bench(dl, a, b)                     # daily SPY, the raw benchmark
    bstats = perf(bench_d, 252)
    # Displayed benchmark folds are the daily ones; each strategy is compared
    # against the benchmark resampled to that strategy's own frequency.
    bfolds = [perf(slice_eq(bench_d, fa, fb), 252) for fa, fb in FOLDS] if window == BUILD else None
    rows = []
    for name, fn in STRATS:
        npy = FREQ[name]
        use_shy = (npy == 12)          # registered cash asset, per gate2_registration.md
        eq, exp = fn(dl, ml, a, b)
        st = perf(eq, npy)
        bench_f = resample_eq(bench_d, npy)
        folds, folds2 = [], []
        if window == BUILD:
            for (fa, fb) in FOLDS:
                se = slice_eq(eq, fa, fb)
                sf = perf(se, npy)
                # --- Gate 1: unmatched, versus 100%-invested SPY (unchanged) ---
                bf = perf(slice_eq(bench_f, fa, fb), npy)
                if sf is None or bf is None:
                    folds.append(None)
                else:
                    folds.append(dict(sortino=sf["sortino"], dd=sf["max_dd"],
                                      bench_sortino=bf["sortino"], bench_dd=bf["max_dd"],
                                      beats=bool(sf["sortino"] is not None and bf["sortino"] is not None
                                                 and sf["sortino"] > bf["sortino"] and sf["max_dd"] < bf["max_dd"])))
                # --- Gate 2: versus a benchmark matched to this fold's exposure ---
                xs = slice_exp(eq, exp, fa, fb)
                if sf is None or not xs:
                    folds2.append(None); continue
                e = sum(xs) / len(xs)
                b2 = perf(matched_bench_eq([d for d, _ in se], e, dl, ml, use_shy), npy)
                if b2 is None:
                    folds2.append(None); continue
                folds2.append(dict(exposure=round(e, 3),
                                   sortino=sf["sortino"], dd=sf["max_dd"],
                                   bench_sortino=b2["sortino"], bench_dd=b2["max_dd"],
                                   beats=bool(sf["sortino"] is not None and b2["sortino"] is not None
                                              and sf["sortino"] > b2["sortino"] and sf["max_dd"] < b2["max_dd"])))
        rows.append(dict(name=name, freq=npy, stats=st,
                         exposure=round(sum(exp) / len(exp), 3) if exp else None,
                         folds=folds, folds_beaten=sum(1 for f in folds if f and f["beats"]),
                         folds2=folds2, folds2_beaten=sum(1 for f in folds2 if f and f["beats"])))
    return dict(bench=bstats, bench_folds=bfolds, rows=rows)

if __name__ == "__main__":
    import sys
    win = BUILD if (len(sys.argv) < 2 or sys.argv[1] == "build") else VALID
    r = evaluate(win)
    print("SPY benchmark:", r["bench"])
    if r["bench_folds"]:
        print("SPY folds:", [(f["sortino"], f["max_dd"]) for f in r["bench_folds"]])
    print(f"\n{'strategy':22s} {'cagr':>7s} {'maxdd':>6s} {'srt':>6s} {'expo':>6s} "
          f"{'G1':>3s} {'G2':>3s}   gate2 fold exposure")
    print("-" * 86)
    for row in sorted(r["rows"], key=lambda x: -(x["stats"]["sortino"] or -9)):
        s = row["stats"]
        g1, g2 = row["folds_beaten"], row["folds2_beaten"]
        ex = " ".join(f"{f['exposure']:.2f}{'*' if f['beats'] else ' '}" if f else "  -  "
                      for f in row["folds2"]) if row["folds2"] else ""
        flag = ""
        if g1 >= 3 and g2 >= 3: flag = "  PASSES BOTH"
        elif g1 >= 3: flag = "  gate1 only"
        elif g2 >= 3: flag = "  gate2 only"
        print(f"{row['name']:22s} {s['cagr']:+6.1%} {s['max_dd']:5.1%} {str(s['sortino']):>6s} "
              f"{row['exposure']:>6.2f} {g1:>3d} {g2:>3d}   {ex}{flag}")
    print("\nG1 = folds won vs 100%-invested SPY (registered gate, unchanged)")
    print("G2 = folds won vs an exposure-matched benchmark (gate2_registration.md)")
    print("* marks a fold won under Gate 2. Pass mark for either gate is 3 of 4.")
    out = "strategies_build.json" if win == BUILD else "strategies_valid.json"
    json.dump(r, open(os.path.join(os.path.dirname(__file__), "..", "charts", out), "w"), indent=1)
