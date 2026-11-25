"""LogSeal dashboard console (Material You Expressive bento layout, projector-safe).
Run: streamlit run app.py --server.port 8501
Options: LOGSEAL_CONFIG=config.local.json (env) | ?stage=1 hides the sidebar | ?mock=ok|edit|rewrite|offline tests without a backend"""
import calendar
import html
import json
import os
import time
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.environ.get("LOGSEAL_CONFIG", os.path.join(HERE, "config.json"))

# Material You Expressive tonal palette (neutral off-white surfaces; color only where attention is needed)
SAGE, OCHRE, SLATE_TEAL, OFFLINE_ACC = "#2E6F51", "#9E6320", "#4A6E7D", "#6B726D"
CLAY, CLAY_BG, CLAY_BD = "#B34740", "#F8EAE8", "#E2BAB6"

try:
    import seal
    from verify import verify as _real_verify
except ImportError:
    _real_verify = None


def _mock(kind):
    h = lambda c: c * 64
    edit, rewrite, offline = kind == "edit", kind == "rewrite", kind == "offline"
    vh = h("b") if rewrite else h("a")
    nodes = [
        {"name": "Server", "role": "server", "reachable": True, "head_seq": 412, "head_hash": h("a"), "agrees": not edit},
        {"name": "Vault 1", "role": "vault", "reachable": True, "head_seq": 412, "head_hash": vh, "agrees": not rewrite},
        {"name": "Vault 2", "role": "vault", "reachable": not offline, "head_seq": None if offline else 412,
         "head_hash": None if offline else vh, "agrees": None if offline else not rewrite},
    ]
    if edit:
        fnd = [{"class": "EDIT", "seq": 120, "expected": h("a"), "actual": h("b"),
                "detail": "Record 120 was changed after it was sealed.", "confirmed_by": ["Vault 1", "Vault 2"]}]
    elif rewrite:
        fnd = [{"class": "WITNESS_CONFLICT", "seq": 120, "expected": h("b"), "actual": h("a"),
                "detail": "The server's records were rewritten: the vaults remember record 120 differently.",
                "confirmed_by": ["Vault 1", "Vault 2"]}]
    else:
        fnd = []
    feed = [{"seq": i, "ts": f"2026-11-25T10:31:{i % 60:02d}",
             "event": "login_fail" if i % 7 == 0 else ("sudo" if i % 11 == 0 else "file_read"),
             "user": "alice", "src_ip": "10.0.0.7", "ok": not (fnd and i == 120)} for i in range(100, 130)]
    return {"status": "TAMPERED" if fnd else "OK", "checked_at": "mock", "log_lines": 412, "ledger_entries": 412,
            "findings": fnd, "nodes": nodes, "feed": feed}


def run_verify(mock):
    if mock:
        return _mock(mock)
    if _real_verify is None:
        raise RuntimeError("verify.py is not available")
    return _real_verify(seal.load_config(CFG))


def short(x, full=False):
    return "none" if not x else (x if full else x[:8])


def read_log_text():
    try:
        cfg = seal.load_config(CFG)
        with open(cfg["log_path"], "rb") as f:
            return f.read().decode("utf-8", "replace").split("\n")
    except Exception:
        return []


def seen_path():
    """Display-only cache lives next to the log, so parallel stacks cannot overwrite each other."""
    try:
        cfg = seal.load_config(CFG)
        return os.path.join(os.path.dirname(os.path.abspath(cfg["log_path"])), ".seen_lines.json")
    except Exception:
        return os.path.join(HERE, ".seen_lines.json")


def _summary_stats():
    out = {"bench": None, "metrics": None}
    for key, fname in (("bench", "bench.json"), ("metrics", "metrics.json")):
        p = os.path.join(HERE, fname)
        if os.path.exists(p):
            try:
                with open(p) as fh:
                    out[key] = json.load(fh)
            except Exception:
                pass
    return out


def css():
    st.markdown("""<style>
    :root {
        --m3-bg: #FAF9F6;
        --m3-surf: #FFFFFF;
        --m3-surf-low: #F2F1ED;
        --m3-ink: #1C201D;
        --m3-ink-muted: #4D534E;
        --m3-outline: #DEDCD5;
    }
    html, body, [class*="css"] {
        font-size: 20px;
        font-family: "Segoe UI Variable", "Segoe UI", system-ui, -apple-system, sans-serif;
    }
    .stApp {background: var(--m3-bg); color: var(--m3-ink);}
    [data-testid="stSidebar"] {background: var(--m3-surf-low); border-right: 1px solid var(--m3-outline);}
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--m3-surf);
        border-color: var(--m3-outline) !important;
        border-radius: 6px !important;
        box-shadow: 0 1px 3px rgba(28,32,29,.03);
    }
    .block-container {padding-top: 1.0rem; padding-bottom: 1.6rem; max-width: 1480px;}
    header[data-testid="stHeader"] {background: transparent; height: 2.0rem;}
    #MainMenu, footer, [data-testid="stToolbar"] {visibility: hidden;}

    .dash-head {display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;
                background:var(--m3-surf); border:1px solid var(--m3-outline); border-radius:6px;
                padding:10px 18px; margin-bottom:10px; box-shadow:0 1px 3px rgba(28,32,29,.03);}
    .brand {display:flex; align-items:center; gap:12px; font-size:24px; font-weight:800;
            letter-spacing:-0.02em; color:var(--m3-ink);}
    .brand-mark {display:inline-flex; align-items:center; justify-content:center; width:34px; height:34px;
                 border-radius:5px; background:var(--m3-surf-low); border:1px solid var(--m3-outline);
                 color:var(--m3-ink); font-size:18px; font-weight:900;}
    .brand-tag {font-size:15px; font-weight:600; color:var(--m3-ink-muted);}
    .telem {display:flex; align-items:center; flex-wrap:wrap; gap:8px;}
    .pill {display:inline-flex; align-items:center; gap:6px; padding:4px 10px; border-radius:4px;
           font-size:14px; font-weight:700;}
    .pill-live {background:var(--m3-surf-low); color:var(--m3-ink); border:1px solid var(--m3-outline);}
    .pill-mock {background:#F6ECDC; color:#633C10; border:1px solid #DEC39A;}
    .pill-stat {background:var(--m3-surf-low); color:var(--m3-ink); border:1px solid var(--m3-outline);}

    .steps {display:grid; grid-template-columns:1fr auto 1fr auto 1fr; align-items:stretch; gap:8px; margin-bottom:12px;}
    .step {border-radius:6px; padding:9px 14px; border:1px solid var(--m3-outline); background:var(--m3-surf);
           display:flex; align-items:center; gap:10px;}
    .step-chip {font-size:12px; font-weight:800; letter-spacing:.06em; text-transform:uppercase;
                padding:4px 9px; border-radius:4px; white-space:nowrap;
                background:var(--m3-surf-low); color:var(--m3-ink); border:1px solid var(--m3-outline);}
    .step-t {font-size:17px; font-weight:800; color:var(--m3-ink); line-height:1.1;}
    .step-d {font-size:15px; color:var(--m3-ink-muted); line-height:1.2;}
    .step-arr {display:flex; align-items:center; justify-content:center; font-size:18px; font-weight:800; color:#7A807B;}

    .hero-grid {display:grid; grid-template-columns:1.45fr 1fr; gap:14px; margin-bottom:14px; align-items:stretch;}
    .banner {border-radius:6px; padding:22px 26px; display:flex; flex-direction:column; justify-content:center;
             box-shadow:0 2px 10px rgba(28,32,29,.06);}
    .banner-kicker {font-size:13px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; opacity:.86; margin-bottom:4px;}
    .banner-main {font-size:48px; font-weight:900; letter-spacing:-0.02em; line-height:1.05;}
    .banner-sub {font-size:19px; font-weight:600; opacity:.94; margin-top:6px;}
    @keyframes soft-pulse {
        0%,100% {box-shadow:0 0 0 0 rgba(179,71,64,.38);}
        50% {box-shadow:0 0 0 8px rgba(179,71,64,0);}
    }
    .pulse {animation: soft-pulse 1.6s ease-in-out infinite;}

    .kpi-grid {display:grid; grid-template-columns:1fr 1fr; gap:12px;}
    .kpi {background:var(--m3-surf); border:1px solid var(--m3-outline); border-radius:6px; padding:13px 16px;
          display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 1px 3px rgba(28,32,29,.03);}
    .kpi-lbl {font-size:13px; font-weight:800; letter-spacing:.05em; text-transform:uppercase; color:var(--m3-ink-muted);}
    .kpi-val {font-size:32px; font-weight:900; letter-spacing:-0.02em; line-height:1.15; margin:2px 0; color:var(--m3-ink);}
    .kpi-sub {font-size:15px; font-weight:600; color:var(--m3-ink-muted);}

    .tiles {display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:14px; margin-bottom:14px;}
    .tile {border-radius:6px; border:1px solid; padding:14px 18px; box-shadow:0 1px 3px rgba(28,32,29,.03);}
    .tile-top {display:flex; justify-content:space-between; align-items:center; gap:8px; margin-bottom:8px;}
    .role-badge {font-size:12px; font-weight:800; letter-spacing:.06em; padding:3px 8px; border-radius:4px;
                 background:var(--m3-surf-low); color:var(--m3-ink-muted); border:1px solid var(--m3-outline);}
    .state-badge {font-size:12px; font-weight:800; letter-spacing:.04em; padding:3px 8px; border-radius:4px;}
    .tile-mid {display:flex; justify-content:space-between; align-items:center; gap:12px;}
    .tile .n {font-size:26px; font-weight:800; letter-spacing:-0.015em; color:var(--m3-ink);}
    .tile .rec {font-size:19px; font-weight:700; color:var(--m3-ink-muted); margin-top:2px;}
    .tile .tick {font-size:40px; line-height:1; font-weight:900;}
    .tile .fp {display:inline-block; margin-top:10px; font-family:ui-monospace, Consolas, monospace; font-size:18px; font-weight:700;
               color:var(--m3-ink); background:var(--m3-bg); border:1px solid var(--m3-outline);
               border-radius:4px; padding:3px 10px; max-width:100%; word-break:break-all;}

    .beforeafter {font-size:18px; font-weight:700; color:var(--m3-ink); margin:8px 0 4px;}

    .panel {background:var(--m3-surf); border:1px solid var(--m3-outline); border-radius:6px; padding:16px 18px;
            box-shadow:0 1px 3px rgba(28,32,29,.03);}
    .panel-hdr {display:flex; justify-content:space-between; align-items:center; gap:8px; margin-bottom:10px;}
    .panel-title {font-size:21px; font-weight:800; letter-spacing:-0.01em; color:var(--m3-ink); margin:0;}
    .panel-sub {font-size:14px; font-weight:700; color:var(--m3-ink-muted);}
    .feed-scroll {max-height:420px; overflow-y:auto; border-radius:4px; border:1px solid #ECEAE4;}
    table.feed {width:100%; border-collapse:separate; border-spacing:0; font-size:18px;}
    table.feed th {position:sticky; top:0; z-index:1; background:var(--m3-surf-low); color:var(--m3-ink-muted);
                   font-size:13px; text-transform:uppercase; letter-spacing:.05em; font-weight:800;
                   padding:9px 11px; text-align:left; border-bottom:1px solid var(--m3-outline);}
    table.feed td {padding:8px 11px; border-bottom:1px solid #ECEAE4; color:var(--m3-ink); vertical-align:middle;}
    table.feed tr:nth-child(even) td {background:#FAF9F6;}
    table.feed tr.bad td {background:#F8EAE8 !important; color:#6E2622; font-weight:700;}
    .mono {font-family:ui-monospace, Consolas, monospace; font-weight:600;}
    .ev-badge {display:inline-block; padding:2px 8px; border-radius:4px; font-size:14px; font-weight:700;}
    .ev-ok {background:var(--m3-surf-low); color:var(--m3-ink-muted); border:1px solid var(--m3-outline);}
    .ev-bad {background:#B34740; color:#FFF9F8;}
    .ev-warn {background:#F6ECDC; color:#633C10; border:1px solid #DEC39A;}
    .ev-priv {background:var(--m3-surf-low); color:var(--m3-ink); border:1px solid var(--m3-outline);}
    .ev-norm {background:var(--m3-surf-low); color:var(--m3-ink-muted); border:1px solid var(--m3-outline);}

    .burst-ok {background:var(--m3-surf-low); border:1px solid var(--m3-outline); border-radius:4px; padding:10px 14px;
               margin-top:8px; color:var(--m3-ink-muted); font-size:17px; font-weight:600;}
    .burst-alert {background:#F6ECDC; border:1px solid #DEC39A; border-radius:4px;
                  padding:10px 14px; margin-top:8px; color:#633C10; font-size:18px; font-weight:700;}
    .mix-chips {display:flex; flex-wrap:wrap; gap:8px; margin-top:10px;}
    .mix-chip {background:var(--m3-surf-low); border:1px solid var(--m3-outline); border-radius:4px;
               padding:5px 10px; font-size:15px; font-weight:700; color:var(--m3-ink);}

    .notif-stack {display:flex; flex-direction:column; gap:8px; margin-bottom:12px;}
    .notif {display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;
            border-radius:6px; border:1px solid; border-left-width:5px; padding:10px 16px;
            box-shadow:0 1px 3px rgba(28,32,29,.04);}
    .notif-ok {background:var(--m3-surf); border-color:var(--m3-outline); border-left-color:#2E6F51; color:var(--m3-ink);}
    .notif-warn {background:#F6ECDC; border-color:#DEC39A; border-left-color:#9E6320; color:#633C10;}
    .notif-crit {background:#F8EAE8; border-color:#E2BAB6; border-left-color:#B34740; color:#6E2622;}
    .notif-info {background:var(--m3-surf); border-color:var(--m3-outline); border-left-color:#4A6E7D; color:var(--m3-ink);}
    .notif-main {display:flex; align-items:center; flex-wrap:wrap; gap:10px; font-size:17px; font-weight:600;}
    .notif-tag {font-size:12px; font-weight:800; letter-spacing:.05em; text-transform:uppercase;
                padding:3px 9px; border-radius:4px; white-space:nowrap;}
    .notif-tag-ok {background:var(--m3-surf-low); color:#1C4A35; border:1px solid var(--m3-outline);}
    .notif-tag-warn {background:#9E6320; color:#FFFDF9;}
    .notif-tag-crit {background:#B34740; color:#FFF9F8;}
    .notif-tag-info {background:var(--m3-surf-low); color:#23404C; border:1px solid var(--m3-outline);}
    .notif-meta {display:flex; align-items:center; flex-wrap:wrap; gap:8px; font-size:14px; font-weight:700;}
    .notif-chip {background:rgba(255,255,255,.88); border:1px solid var(--m3-outline); border-radius:4px;
                 padding:3px 8px; font-family:ui-monospace, Consolas, monospace; color:var(--m3-ink);}

    @media (max-width: 980px) {
        .hero-grid, .tiles, .steps {grid-template-columns:1fr;}
        .step-arr {display:none;}
        .banner-main {font-size:36px;}
    }
    </style>""", unsafe_allow_html=True)


def steps():
    items = [
        ("01 RECORD", "Every action is written to a log"),
        ("02 SEAL", "A fingerprint of each record is sent to independent vaults"),
        ("03 COMPARE", "If anything changes, the machines disagree"),
    ]
    parts = []
    for i, (k, d) in enumerate(items):
        parts.append(
            f'<div class="step">'
            f'<span class="step-chip">{k}</span>'
            f'<div class="step-d">{d}</div></div>'
        )
        if i < len(items) - 1:
            parts.append('<div class="step-arr">&rarr;</div>')
    st.markdown('<div class="steps">' + "".join(parts) + "</div>", unsafe_allow_html=True)


def header_bar(r, mock, stage):
    online = sum(1 for n in r["nodes"] if n["role"] == "vault" and n.get("reachable"))
    total_v = sum(1 for n in r["nodes"] if n["role"] == "vault")
    mode_pill = (
        f'<span class="pill pill-mock">MOCK: {html.escape(mock.upper())}</span>'
        if mock else f'<span class="pill pill-live"><span style="color:{SAGE}">&#9679;</span> LIVE &middot; 2s REFRESH</span>'
    )
    brand_html = (
        '<div class="brand"><span class="brand-mark">&#128737;</span>LogSeal <span class="brand-tag">Stage View</span></div>'
        if stage else '<div class="brand"><span class="brand-mark">&#128737;</span>LogSeal <span class="brand-tag">Security Integrity Dashboard</span></div>'
    )
    checked = html.escape(str(r.get("checked_at") or ""))
    st.markdown(
        f'<div class="dash-head">{brand_html}'
        f'<div class="telem">{mode_pill}'
        f'<span class="pill pill-stat">Vaults: {online}/{total_v} online</span>'
        f'<span class="pill pill-stat">Checked: {checked}</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def hero_and_kpis(r, stats):
    meta = {
        "OK": ("ALL RECORDS INTACT", "Every sealed record matches across the server and active vaults.", SAGE, "#FAFDFB", "", "&#10004;"),
        "PENDING": ("SEALING...", "A newly written record is waiting for seal confirmation.", OCHRE, "#FFFDF9", "", "&#9203;"),
        "TAMPERED": ("TAMPERING DETECTED", "Cryptographic mismatch detected — inspect the forensic alert below.", CLAY, "#FFF9F8", "pulse", "&#9888;"),
    }.get(r.get("status"), ("CHECKING...", "Verifying log chain and vaults.", SLATE_TEAL, "#F8FBFD", "", "&#8987;"))
    txt, sub, bg, fg, cls, ico = meta

    n_nodes = len(r["nodes"])
    reachable_nodes = [n for n in r["nodes"] if n.get("agrees") is not None]
    agree_count = sum(1 for n in reachable_nodes if n.get("agrees") is True)
    n_find = len(r.get("findings") or [])

    cons_color = "#1C201D" if agree_count == len(reachable_nodes) and reachable_nodes else CLAY
    find_color = "#1C201D" if n_find == 0 else CLAY
    find_sub = "Zero tamper findings" if n_find == 0 else "Action required below"

    bench = stats.get("bench")
    metrics = stats.get("metrics")
    if bench:
        qa_val = f"{bench.get('detected')}/{bench.get('mutations')}"
        qa_sub = f"Mutations caught ({bench.get('latency_ms_median')} ms)"
    elif metrics:
        qa_val = f"F1 {metrics.get('f1')}"
        qa_sub = f"Burst detector recall {metrics.get('recall')}"
    else:
        qa_val = "2s"
        qa_sub = "Auto-verification cycle"

    st.markdown(
        f'<div class="hero-grid">'
        f'<div class="banner {cls}" style="background:{bg};color:{fg}">'
        f'<div class="banner-kicker">INTEGRITY VERDICT</div>'
        f'<div class="banner-main">{ico} {txt}</div>'
        f'<div class="banner-sub">{html.escape(sub)}</div></div>'
        f'<div class="kpi-grid">'
        f'<div class="kpi"><div class="kpi-lbl">Sealed Records</div>'
        f'<div class="kpi-val">{int(r.get("log_lines", 0))}</div>'
        f'<div class="kpi-sub">Ledger entries: {int(r.get("ledger_entries", 0))}</div></div>'
        f'<div class="kpi"><div class="kpi-lbl">Machine Consensus</div>'
        f'<div class="kpi-val" style="color:{cons_color}">{agree_count}/{n_nodes}</div>'
        f'<div class="kpi-sub">{len(reachable_nodes)}/{n_nodes} nodes reachable</div></div>'
        f'<div class="kpi"><div class="kpi-lbl">Active Alerts</div>'
        f'<div class="kpi-val" style="color:{find_color}">{n_find}</div>'
        f'<div class="kpi-sub">{find_sub}</div></div>'
        f'<div class="kpi"><div class="kpi-lbl">Audit Benchmark</div>'
        f'<div class="kpi-val">{html.escape(qa_val)}</div>'
        f'<div class="kpi-sub">{html.escape(qa_sub)}</div></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def tiles(r, raw):
    out = []
    for n in r["nodes"]:
        ag = n["agrees"]
        role = "PRIMARY SERVER" if n.get("role") == "server" else "INDEPENDENT VAULT"
        if ag is None:
            bg, bd, badge_bg, badge_fg, tick_col, state, tick = "#F2F1ED", "#D4D2CA", "#EAE8E1", "#4D534E", OFFLINE_ACC, "OFFLINE", "OFFLINE"
        elif ag:
            bg, bd, badge_bg, badge_fg, tick_col, state, tick = "#FFFFFF", "#DEDCD5", "#F2F1ED", "#1C201D", SAGE, "SYNCED", "&#10004;"
        else:
            bg, bd, badge_bg, badge_fg, tick_col, state, tick = CLAY_BG, CLAY_BD, CLAY, "#FFFFFF", CLAY, "MISMATCH", "&#10008;"
        rec = "Unreachable" if ag is None else f"Record #{n['head_seq']}"
        fp = "No response" if ag is None else short(n["head_hash"], raw)
        tick_style = f"color:{tick_col};" + ("font-size:24px;" if ag is None else "")
        out.append(
            f'<div class="tile" style="border-color:{bd};background:{bg}">'
            f'<div class="tile-top"><span class="role-badge">{role}</span>'
            f'<span class="state-badge" style="background:{badge_bg};color:{badge_fg}">{state}</span></div>'
            f'<div class="tile-mid"><div><div class="n">{html.escape(n["name"])}</div>'
            f'<div class="rec">{rec}</div></div><div class="tick" style="{tick_style}">{tick}</div></div>'
            f'<div class="fp">{html.escape(fp)}</div></div>'
        )
    st.markdown('<div class="tiles">' + "".join(out) + "</div>", unsafe_allow_html=True)


def _event_pill(ev_raw, ok):
    if not ok and ev_raw == "UNPARSEABLE":
        return '<span class="ev-badge ev-bad">UNREADABLE</span>'
    ev = html.escape(str(ev_raw))
    if ev_raw == "login_fail":
        return f'<span class="ev-badge ev-warn">{ev}</span>'
    if ev_raw in ("sudo", "config_change"):
        return f'<span class="ev-badge ev-priv">{ev}</span>'
    return f'<span class="ev-badge ev-norm">{ev}</span>'


def feed(r):
    rows = []
    recent = r["feed"][-20:]
    for x in reversed(recent):
        ok = x.get("ok", True)
        status_pill = '<span class="ev-badge ev-ok">SEALED</span>' if ok else '<span class="ev-badge ev-bad">TAMPERED</span>'
        ev_html = _event_pill(x["event"], ok)
        rows.append(
            f'<tr class="{"bad" if not ok else ""}">'
            f'<td>{status_pill}</td>'
            f'<td class="mono">#{x["seq"]}</td>'
            f'<td class="mono">{html.escape(str(x.get("ts") or "")[11:19])}</td>'
            f'<td><b>{html.escape(str(x.get("user") or ""))}</b></td>'
            f'<td>{ev_html}</td>'
            f'<td class="mono">{html.escape(str(x.get("src_ip") or ""))}</td>'
            f'</tr>'
        )
    if not rows:
        body = '<div style="font-size:20px;color:#4B544D;padding:16px 8px;">Waiting for incoming security events...</div>'
    else:
        body = (
            '<div class="feed-scroll"><table class="feed">'
            '<tr><th>Status</th><th>Seq</th><th>Time</th><th>User</th><th>Event</th><th>IP</th></tr>'
            + "".join(rows) + "</table></div>"
        )
    st.markdown(
        f'<div class="panel"><div class="panel-hdr"><div class="panel-title">Live Audit Stream</div>'
        f'<div class="panel-sub">Latest {len(recent)} records</div></div>{body}</div>',
        unsafe_allow_html=True,
    )


def _analyze_activity(lines, r, mock):
    evs = []
    if mock:
        for row in r.get("feed") or []:
            if row.get("ts") and row.get("event") != "UNPARSEABLE":
                evs.append(row)
    else:
        for ln in lines[-400:]:
            try:
                evs.append(json.loads(ln))
            except Exception:
                pass
    cnt, mix = {}, {}
    for e in evs:
        ev_name = str(e.get("event") or "unknown")
        mix[ev_name] = mix.get(ev_name, 0) + 1
        try:
            s = calendar.timegm(time.strptime(e["ts"], "%Y-%m-%dT%H:%M:%S")) // 10 * 10
            cnt[s] = cnt.get(s, 0) + 1
        except Exception:
            continue
    flagged_set, model_missing = set(), False
    if evs and not mock:
        try:
            import ml
            flagged_windows = [w for w in ml.flag_windows(evs) if w["flagged"]]
            flagged_set = {w["window_start"][11:19] for w in flagged_windows}
        except FileNotFoundError:
            model_missing = True
        except Exception:
            pass
    return evs, cnt, mix, flagged_set, model_missing


def notifications(r, raw, lines, act, mock=None):
    """Notification strip placed directly below the nav bar for tampering & important events."""
    _evs, _cnt, _mix, flagged_set, _model_missing = act
    items = []

    for fnd in r.get("findings") or []:
        cls_name = html.escape(str(fnd.get("class", "ALERT")))
        seq = int(fnd.get("seq", 0))
        conf = ", ".join(fnd.get("confirmed_by") or []) or "no vault"
        meta = (
            f'<span class="notif-chip">Now: {html.escape(short(fnd.get("actual"), raw))}</span>'
            f'<span class="notif-chip">Expect: {html.escape(short(fnd.get("expected"), raw))}</span>'
            f'<span class="notif-chip">By: {html.escape(conf)}</span>'
        )
        items.append(
            f'<div class="notif notif-crit">'
            f'<div class="notif-main"><span class="notif-tag notif-tag-crit">&#9888; {cls_name} &middot; #{seq}</span>'
            f'<span>{html.escape(fnd["detail"])}</span></div>'
            f'<div class="notif-meta">{meta}</div></div>'
        )

    offline = [n["name"] for n in r.get("nodes") or [] if n.get("agrees") is None]
    if offline:
        names = ", ".join(html.escape(x) for x in offline)
        items.append(
            f'<div class="notif notif-warn">'
            f'<div class="notif-main"><span class="notif-tag notif-tag-warn">VAULT OFFLINE</span>'
            f'<span>{names} unreachable — surviving nodes continue verifying.</span></div></div>'
        )

    if flagged_set:
        times = ", ".join(sorted(flagged_set)[-4:])
        items.append(
            f'<div class="notif notif-warn">'
            f'<div class="notif-main"><span class="notif-tag notif-tag-warn">&#9888; ML BURST</span>'
            f'<span>Suspicious failed-login spike flagged around {html.escape(times)}.</span></div></div>'
        )

    if r.get("status") == "PENDING":
        items.append(
            '<div class="notif notif-warn">'
            '<div class="notif-main"><span class="notif-tag notif-tag-warn">SEALING</span>'
            '<span>New log line detected — waiting up to 3s for ledger and vault confirmation.</span></div></div>'
        )

    notable = [
        f'#{x["seq"]} {x["event"]} ({x.get("user") or "?"})'
        for x in reversed((r.get("feed") or [])[-10:])
        if x.get("event") in ("sudo", "config_change", "login_fail", "UNPARSEABLE")
    ][:3]

    if not items:
        extra = f'<div class="notif-meta"><span class="notif-chip">Recent: {html.escape(" · ".join(notable))}</span></div>' if notable else ""
        items.append(
            f'<div class="notif notif-ok">'
            f'<div class="notif-main"><span class="notif-tag notif-tag-ok">&#10004; ALL CLEAR</span>'
            f'<span>No tampering, no missing vaults, and no anomalous login bursts.</span></div>{extra}</div>'
        )
    elif notable and not r.get("findings"):
        items.append(
            f'<div class="notif notif-info">'
            f'<div class="notif-main"><span class="notif-tag notif-tag-info">NOTABLE EVENTS</span>'
            f'<span>{html.escape(" · ".join(notable))}</span></div></div>'
        )

    st.markdown('<div class="notif-stack">' + "".join(items) + "</div>", unsafe_allow_html=True)

    if r.get("findings") and not mock:
        try:
            with open(seen_path()) as f:
                seen = json.load(f)
        except Exception:
            seen = {}
        for fnd in r["findings"]:
            seq = int(fnd.get("seq", 0))
            old = seen.get(str(seq))
            now = lines[seq - 1] if 0 < seq <= len(lines) else None
            if fnd.get("class") == "EDIT" and old and now:
                st.markdown(f'<p class="beforeafter">Record #{seq} before / after (display only; proof is the fingerprint mismatch)</p>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                c1.code(old, language="json")
                c2.code(now, language="json")


def activity(act):
    """Optional: events per 10 s window + suspicious windows from ml.py. Cut first if late."""
    import pandas as pd

    evs, cnt, mix, flagged_set, model_missing = act
    if not evs:
        with st.container(border=True):
            st.markdown('<div class="panel-title">Activity &amp; AI Burst Triage</div>'
                        '<div class="panel-sub">Waiting for sealed events to plot 10s activity windows.</div>',
                        unsafe_allow_html=True)
        return
    if not cnt:
        return

    rows = []
    for k, v in sorted(cnt.items()):
        lbl = time.strftime("%H:%M:%S", time.gmtime(k))
        rows.append({"Window": lbl, "Events": v, "State": "Suspicious Burst" if lbl in flagged_set else "Normal"})
    df = pd.DataFrame(rows)

    with st.container(border=True):
        st.markdown('<div class="panel-hdr"><div class="panel-title">Activity &amp; AI Burst Triage</div>'
                    f'<div class="panel-sub">Last {len(evs)} events (10s bins)</div></div>',
                    unsafe_allow_html=True)
        try:
            import altair as alt
            chart = (
                alt.Chart(df)
                .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
                .encode(
                    x=alt.X("Window:N", sort=None, axis=alt.Axis(labelAngle=-30, labelFontSize=13, titleFontSize=14, title="Window")),
                    y=alt.Y("Events:Q", axis=alt.Axis(labelFontSize=13, titleFontSize=14, title="Events / 10s")),
                    color=alt.Color(
                        "State:N",
                        scale=alt.Scale(domain=["Normal", "Suspicious Burst"], range=["#8A908C", "#C27D2E"]),
                        legend=alt.Legend(orient="top", title=None, labelFontSize=14),
                    ),
                    tooltip=["Window", "Events", "State"],
                )
                .properties(height=250)
                .configure_view(strokeWidth=0)
                .configure_axis(labelColor="#1C201D", titleColor="#1C201D", gridColor="#ECEAE4")
                .configure_legend(labelColor="#1C201D")
            )
            st.altair_chart(chart, width="stretch")
        except Exception:
            st.bar_chart(df.set_index("Window")["Events"])

        chips = "".join(
            f'<span class="mix-chip">{html.escape(k)}: {v}</span>'
            for k, v in sorted(mix.items(), key=lambda kv: -kv[1])[:6]
        )
        st.markdown(f'<div class="mix-chips">{chips}</div>', unsafe_allow_html=True)

        if model_missing:
            st.markdown(
                '<div class="burst-alert">Model not trained. Run <code>make dataset</code> then <code>make train</code>.</div>',
                unsafe_allow_html=True,
            )
        elif flagged_set:
            times = sorted(flagged_set)
            st.markdown(
                f'<div class="burst-alert">&#9888; Suspicious burst of failed logins flagged around {", ".join(times[-4:])}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="burst-ok">&#10004; IsolationForest check: no brute-force login burst detected in recent windows.</div>',
                unsafe_allow_html=True,
            )


def dashboard(raw, mock, chart, stage):
    try:
        r = run_verify(mock)
    except Exception as e:
        st.warning(f"Verifier is not available right now ({type(e).__name__}). Retrying...")
        return
    lines = [] if mock else read_log_text()
    if r["status"] == "OK" and not mock:                       # remember what clean lines looked like (display only)
        try:
            base = max(0, len(lines) - 201)
            with open(seen_path(), "w") as f:
                json.dump({str(i + 1): l for i, l in enumerate(lines[base:], base)}, f)
        except Exception:
            pass

    stats = _summary_stats()
    act = _analyze_activity(lines, r, mock)
    for section in (
        lambda: header_bar(r, mock, stage),
        lambda: notifications(r, raw, lines, act, mock),
        steps,
        lambda: hero_and_kpis(r, stats),
        lambda: tiles(r, raw),
    ):
        try:
            section()
        except Exception as e:
            st.info(f"(section unavailable: {type(e).__name__})")

    if chart:
        left, right = st.columns([1.15, 1.0], gap="medium")
        with left:
            try:
                feed(r)
            except Exception as e:
                st.info(f"(feed unavailable: {type(e).__name__})")
        with right:
            try:
                activity(act)
            except Exception:
                pass
    else:
        try:
            feed(r)
        except Exception as e:
            st.info(f"(feed unavailable: {type(e).__name__})")


def _render_sidebar_metrics():
    with st.expander("Benchmark numbers"):
        for f, label in (("bench.json", "Mutation test"), ("metrics.json", "Burst detector")):
            p = os.path.join(HERE, f)
            st.markdown(f"**{label}**")
            if os.path.exists(p):
                with open(p) as fh:
                    data = json.load(fh)
                if f == "bench.json":
                    c1, c2 = st.columns(2)
                    c1.metric("Detected", f"{data.get('detected')}/{data.get('mutations')}")
                    c2.metric("Median", f"{data.get('latency_ms_median')} ms")
                elif f == "metrics.json":
                    c1, c2 = st.columns(2)
                    c1.metric("F1 (synth)", f"{data.get('f1')}")
                    c2.metric("Recall", f"{data.get('recall')}")
                st.json(data)
            else:
                st.write("not run yet")


st.set_page_config(page_title="LogSeal", layout="wide")
css()
q = st.query_params
stage, mock = q.get("stage") == "1", q.get("mock")
raw, chart = False, True
if stage:
    st.markdown("<style>[data-testid='stSidebar'],[data-testid='collapsedControl']{display:none}</style>", unsafe_allow_html=True)
else:
    with st.sidebar:
        st.title("LogSeal Controls")
        if st.button("Verify now", width="stretch"):
            st.rerun()
        raw = st.toggle("Show raw detail (full hashes)", False)
        chart = st.toggle("Activity & AI burst chart", True)
        _render_sidebar_metrics()
        st.caption("Projector URL: add ?stage=1")
if hasattr(st, "fragment"):
    dashboard = st.fragment(run_every=2)(dashboard)
dashboard(raw, mock, chart, stage)
