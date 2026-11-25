"""LogSeal console (projector-safe). Run: streamlit run app.py --server.port 8501
Options: LOGSEAL_CONFIG=config.local.json (env) | ?stage=1 hides the sidebar | ?mock=ok|edit|rewrite|offline tests without a backend"""
import html, json, os, time
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.environ.get("LOGSEAL_CONFIG", os.path.join(HERE, "config.json"))
GREEN, RED, AMBER, GREY = "#16a34a", "#dc2626", "#d97706", "#64748b"

try:
    import seal
    from verify import verify as _real_verify
except ImportError:
    _real_verify = None

def _mock(kind):
    h = lambda c: c * 64
    edit, rewrite, offline = kind == "edit", kind == "rewrite", kind == "offline"
    vh = h("b") if rewrite else h("a")
    nodes = [{"name": "Server", "role": "server", "reachable": True, "head_seq": 412, "head_hash": h("a"), "agrees": not edit},
             {"name": "Vault 1", "role": "vault", "reachable": True, "head_seq": 412, "head_hash": vh, "agrees": not rewrite},
             {"name": "Vault 2", "role": "vault", "reachable": not offline, "head_seq": None if offline else 412,
              "head_hash": None if offline else vh, "agrees": None if offline else not rewrite}]
    if edit:
        fnd = [{"class": "EDIT", "seq": 120, "expected": h("a"), "actual": h("b"),
                "detail": "Record 120 was changed after it was sealed.", "confirmed_by": ["Vault 1", "Vault 2"]}]
    elif rewrite:
        fnd = [{"class": "WITNESS_CONFLICT", "seq": 120, "expected": h("b"), "actual": h("a"),
                "detail": "The server's records were rewritten: the vaults remember record 120 differently.",
                "confirmed_by": ["Vault 1", "Vault 2"]}]
    else:
        fnd = []
    feed = [{"seq": i, "ts": f"2026-11-25T10:31:{i % 60:02d}", "event": "login_fail" if i % 7 == 0 else "file_read", "user": "alice",
             "src_ip": "10.0.0.7", "ok": not (fnd and i == 120)} for i in range(100, 130)]
    return {"status": "TAMPERED" if fnd else "OK", "checked_at": "mock", "log_lines": 412, "ledger_entries": 412,
            "findings": fnd, "nodes": nodes, "feed": feed}

def run_verify(mock):
    if mock or _real_verify is None:
        return _mock(mock or "ok")
    return _real_verify(seal.load_config(CFG))

def short(x, full=False):
    return "none" if not x else (x if full else x[:8])

def read_log_text():
    try:
        cfg = seal.load_config(CFG)
        return open(cfg["log_path"], "rb").read().decode("utf-8", "replace").split("\n")
    except Exception:
        return []

SEEN = os.path.join(HERE, ".seen_lines.json")      # display-only cache of lines seen while status was OK

def seen_path():
    try:                                            # keep one cache per stack, next to its log
        return os.path.join(os.path.dirname(seal.load_config(CFG)["log_path"]), ".seen_lines.json")
    except Exception:
        return SEEN

def css():
    st.markdown("""<style>
    html, body, [class*="css"] {font-size: 20px;}
    .stApp {background: #f8fafc; color: #0f172a;}
    .steps {display:flex; gap:16px; margin-bottom:12px}
    .step {flex:1; background:#e2e8f0; border-radius:14px; padding:12px 16px}
    .step b {font-size:26px}
    .banner {font-size:56px; font-weight:900; color:#fff; text-align:center; border-radius:20px; padding:18px; margin:10px 0}
    @keyframes pulse {0%,100%{opacity:1} 50%{opacity:.6}}
    .pulse {animation: pulse 1s infinite}
    .tiles {display:flex; gap:16px}
    .tile {flex:1; border-radius:18px; border:6px solid; background:#fff; text-align:center; padding:14px}
    .tile .n {font-size:30px; font-weight:800} .tile .tick {font-size:72px; line-height:1.1} .tile .fp {font-family:monospace; font-size:24px}
    .alarm {background:#fee2e2; border:4px solid #dc2626; border-radius:16px; padding:14px 20px; margin:14px 0; color:#7f1d1d}
    .alarm code {font-size:26px; font-weight:800; color:#7f1d1d}
    .beforeafter {font-size:20px; font-weight:600; color:#334155; margin:8px 0}
    table.feed {width:100%; border-collapse:collapse; font-size:20px} table.feed td, table.feed th {padding:6px 10px; text-align:left}
    table.feed tr.bad {background:#fecaca; color:#7f1d1d; font-weight:700}
    </style>""", unsafe_allow_html=True)

def steps():
    s = [("1 RECORD", "Every action is written to a log"), ("2 SEAL", "A fingerprint of each record is sent to independent vaults"),
         ("3 COMPARE", "If anything changes, the machines disagree")]
    st.markdown('<div class="steps">' + "".join(f'<div class="step"><b>{a}</b><br>{b}</div>' for a, b in s) + "</div>", unsafe_allow_html=True)

def banner(r):
    txt, col, cls = {"OK": ("ALL RECORDS INTACT", GREEN, ""), "PENDING": ("SEALING...", AMBER, ""),
                     "TAMPERED": ("TAMPERING DETECTED", RED, "pulse")}.get(r.get("status"), ("CHECKING...", AMBER, ""))
    st.markdown(f'<div class="banner {cls}" style="background:{col}">{txt}</div>', unsafe_allow_html=True)

def tiles(r, raw):
    out = []
    for n in r["nodes"]:
        ag = n["agrees"]
        col, tick = (GREY, "OFFLINE") if ag is None else ((GREEN, "✔") if ag else (RED, "✘"))
        rec = "" if ag is None else f"Record #{n['head_seq']}"
        fp = "" if ag is None else short(n["head_hash"], raw)
        out.append(f'<div class="tile" style="border-color:{col}"><div class="n">{html.escape(n["name"])}</div><div>{rec}</div>'
                   f'<div class="fp">{fp}</div><div class="tick" style="color:{col};{"font-size:44px" if ag is None else ""}">{tick}</div></div>')
    st.markdown('<div class="tiles">' + "".join(out) + "</div>", unsafe_allow_html=True)

def alarm(r, raw):
    lines = read_log_text()
    try:
        seen = json.load(open(seen_path()))
    except Exception:
        seen = {}
    for f in r["findings"]:
        conf = ", ".join(f.get("confirmed_by") or []) or "no vault"
        st.markdown(f'<div class="alarm"><b>{html.escape(f["detail"])}</b><br>'
                    f'Server\'s file now fingerprints as <code>{short(f.get("actual"), raw)}</code>. '
                    f'Records say it should be <code>{short(f.get("expected"), raw)}</code>. Confirmed by: {html.escape(conf)}.</div>',
                    unsafe_allow_html=True)
        old, now = seen.get(str(f["seq"])), (lines[f["seq"] - 1] if 0 < f["seq"] <= len(lines) else None)
        if f["class"] == "EDIT" and old and now:
            st.markdown('<p class="beforeafter">Before / after (display only; the proof is the fingerprint mismatch)</p>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.code(old, language="json"); c2.code(now, language="json")

def feed(r):
    rows = []
    for x in reversed(r["feed"][-20:]):
        bad = not x.get("ok", True)
        ev = "UNREADABLE" if x["event"] == "UNPARSEABLE" else html.escape(str(x["event"]))
        rows.append(f'<tr class="{"bad" if bad else ""}"><td>{"⚠" if bad else "🔒"}</td><td>#{x["seq"]}</td><td>{html.escape(str(x.get("ts") or "")[11:19])}</td>'
                    f'<td>{html.escape(str(x.get("user") or ""))}</td><td>{ev}</td><td>{html.escape(str(x.get("src_ip") or ""))}</td></tr>')
    st.markdown('<table class="feed"><tr><th></th><th>Record</th><th>Time</th><th>User</th><th>Event</th><th>IP</th></tr>' + "".join(rows) + "</table>",
                unsafe_allow_html=True)

def activity():
    """Optional: events per 10 s window + suspicious windows from ml.py. Cut first if late."""
    import calendar, pandas as pd
    import ml
    evs = []
    for ln in read_log_text()[-400:]:
        try:
            evs.append(json.loads(ln))
        except Exception:
            pass
    if not evs:
        return
    cnt = {}
    for e in evs:
        s = calendar.timegm(time.strptime(e["ts"], "%Y-%m-%dT%H:%M:%S")) // 10 * 10
        cnt[s] = cnt.get(s, 0) + 1
    st.subheader("Activity (events per 10 seconds)")
    st.bar_chart(pd.Series({time.strftime("%H:%M:%S", time.gmtime(k)): v for k, v in sorted(cnt.items())}))
    bad = [w["window_start"][11:19] for w in ml.flag_windows(evs) if w["flagged"]]
    if bad:
        st.markdown(f'<div class="alarm" style="background:#fef3c7;border-color:{AMBER};color:#78350f">Suspicious burst of failed logins around {", ".join(bad[-3:])}</div>',
                    unsafe_allow_html=True)

def dashboard(raw, mock, chart):
    try:
        r = run_verify(mock)
    except Exception as e:
        st.warning(f"Verifier is not available right now ({type(e).__name__}). Retrying...")
        return
    if r["status"] == "OK" and not mock:                       # remember what clean lines looked like (display only)
        try:
            lines = read_log_text()
            base = max(0, len(lines) - 201)
            json.dump({str(i + 1): l for i, l in enumerate(lines[base:], base)}, open(seen_path(), "w"))
        except Exception:
            pass
    for section in (lambda: banner(r), lambda: tiles(r, raw), lambda: alarm(r, raw) if r["findings"] else None, lambda: feed(r)):
        try:
            section()
        except Exception as e:
            st.info(f"(section unavailable: {type(e).__name__})")
    if chart:
        try:
            activity()
        except Exception:
            pass

st.set_page_config(page_title="LogSeal", layout="wide")
css()
q = st.query_params
stage, mock = q.get("stage") == "1", q.get("mock")
raw, chart = False, True
if stage:
    st.markdown("<style>[data-testid='stSidebar'],[data-testid='collapsedControl']{display:none}</style>", unsafe_allow_html=True)
else:
    with st.sidebar:
        st.title("LogSeal")
        st.button("Verify now")
        raw = st.toggle("Show raw detail", False)
        chart = st.toggle("Activity chart", True)
        with st.expander("Benchmark numbers"):
            for f, label in (("bench.json", "Mutation test"), ("metrics.json", "Burst detector")):
                p = os.path.join(HERE, f)
                st.markdown(f"**{label}**")
                st.json(json.load(open(p))) if os.path.exists(p) else st.write("not run yet")
st.title("LogSeal: tamper-evident security log") if not stage else None
steps()
if hasattr(st, "fragment"):
    dashboard = st.fragment(run_every=2)(dashboard)
dashboard(raw, mock, chart)
