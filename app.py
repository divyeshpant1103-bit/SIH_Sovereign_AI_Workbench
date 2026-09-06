"""
Streamlit UI for the Sovereign Workbench agent (SIH26117).

Three panes, one screen, no chat box: Task / Execution trace / Result.
The trace is the product, so it gets the space and the live stream.

Specs:
    MD Files/SIH26117_Streamlit_UI_Spec.md          what is on screen
    MD Files/SIH26117_Streamlit_UI_Visual_Spec.md   how it looks

All styling lives in .streamlit/config.toml (widgets) and THEME_CSS below
(everything else). Delete either and the app still runs, unstyled. No render
path depends on a selector matching.

Run:
    streamlit run app.py
"""

import os

# Set offline env vars before any import that might phone home
# (sentence-transformers / huggingface_hub, pulled in via search.py).
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

import html
import pickle
import socket
import tempfile
from pathlib import Path

import requests
import streamlit as st

from agent import CorruptPDFError, MODEL, NoTextLayerError, OLLAMA_URL, run as run_agent
from search import Retriever

DEFAULT_REQUEST = ("Check this inspection report against our procedures and "
                   "prepare an approval note.")
SAMPLE_DIR = Path("data/inputs")
FAVICON = Path("assets/favicon.png")
NO_SAMPLE = "— choose —"
EMPTY = "awaiting task"


# ----------------------------------------------------------------------
# palette
# ----------------------------------------------------------------------
# Keep PAPER in sync with the theme block in .streamlit/config.toml. Both, or
# the theme is half-applied: config.toml paints the widgets, this paints ours.

PAPER = False

DARK = {
    "bg": "#0B0C0E", "bg2": "#15171B", "line": "#262A31",
    "txt": "#D8DEE6", "dim": "#8A929E", "faint": "#5A616B",
    "action": "#F85149", "alert": "#E3B341", "ok": "#3FB950",
}
LIGHT = {
    "bg": "#FAFAF8", "bg2": "#F2F2EE", "line": "#E0E0DA",
    "txt": "#1B1D21", "dim": "#5F666F", "faint": "#8A9098",
    "action": "#A8501E", "alert": "#B8860B", "ok": "#2E6B3E",
}
PALETTE = LIGHT if PAPER else DARK

SEV_VAR = {
    "action": "var(--action)",
    "alert": "var(--alert)",
    "acceptable": "var(--ok)",
}

st.set_page_config(
    page_title="Sovereign Workbench — SIH26117",
    layout="wide",
    page_icon=str(FAVICON) if FAVICON.exists() else None,
)

ROOT_VARS = ("<style>:root{"
             + "".join(f"--{k}:{v};" for k, v in PALETTE.items())
             + "}</style>")

THEME_CSS = """
<style>
/* --- Streamlit's own chrome. The Deploy button alone costs us the
       "internal tool" read; the status widget is a spinner by another name,
       and the trace is our progress indicator. --- */
[data-testid="stToolbar"], [data-testid="stStatusWidget"] { display:none; }
[data-testid="stHeader"] { background:transparent; height:0; }

/* --- page frame --- */
.stMainBlockContainer, .block-container { padding:24px 32px 32px 32px; max-width:1600px; }

/* --- micro-labels on every widget --- */
[data-testid="stWidgetLabel"] p {
  font-size:10px; letter-spacing:.14em; text-transform:uppercase; color:var(--dim);
}

/* --- inputs: flat, square, hairlined --- */
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
[data-testid="stFileUploaderDropzone"] {
  background:var(--bg2); border:1px solid var(--line); border-radius:0; color:var(--txt);
}
[data-testid="stFileUploaderDropzone"] { padding:12px; }
[data-testid="stTextArea"] textarea { font-size:13px; }

/* --- buttons --- */
.stButton > button, .stDownloadButton > button {
  width:100%; border-radius:0; font-size:12px; font-weight:700;
  letter-spacing:.1em; text-transform:uppercase;
}
.stButton > button[kind="primary"] { color:var(--bg); }

/* --- vertical hairline between the task column and the trace --- */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
  border-left:1px solid var(--line); padding-left:32px;
}

/* --- title, pane headers, rules --- */
.title { font-size:15px; font-weight:700; color:var(--txt); margin:0 0 16px 0; }
.pane {
  font-size:11px; font-weight:700; letter-spacing:.14em; text-transform:uppercase;
  color:var(--dim); border-bottom:1px solid var(--line);
  padding-bottom:6px; margin:0 0 16px 0;
  display:flex; justify-content:space-between; align-items:baseline; gap:16px;
}
.pane .count { font-weight:400; color:var(--faint); letter-spacing:.06em; white-space:nowrap; }
hr.rule { border:none; border-top:1px solid var(--line); margin:24px 0 16px 0; }

/* --- status bar --- */
.statusbar {
  display:flex; gap:32px; flex-wrap:wrap; align-items:baseline;
  border-top:1px solid var(--line); border-bottom:1px solid var(--line);
  padding:10px 0; margin:0 0 24px 0;
}
.statusbar .lbl { font-size:10px; letter-spacing:.14em; color:var(--dim); margin-right:8px; }
.statusbar .val { font-size:12px; color:var(--txt); font-variant-numeric:tabular-nums; }

/* --- run state: the honest replacement for the spinner we don't allow --- */
.runstate {
  font-size:11px; letter-spacing:.14em; text-transform:uppercase;
  margin:8px 0 0 0; font-variant-numeric:tabular-nums;
}

/* --- trace --- */
.trace {
  height:calc(100vh - 360px); min-height:400px; overflow-y:auto;
  display:flex; flex-direction:column-reverse;
  font-size:13px; line-height:1.55; font-variant-numeric:tabular-nums;
}
/* Rows are fed newest-first into a column-reverse box: the view stays pinned to
   the newest line while streaming, with no JavaScript. The auto margin parks a
   short trace at the top instead of floating it at the bottom of an empty pane,
   and collapses to 0 once the content overflows, so nothing becomes unreachable. */
.trace > :first-child { margin-bottom:auto; }
.ev { display:grid; grid-template-columns:5rem 14rem 1fr; gap:12px; padding:1px 0; }
.ev .t { color:var(--dim); text-align:right; }
.ev .e { color:var(--txt); }
.ev .d { color:var(--dim); word-break:break-word; }
.ev .k { color:var(--faint); }
.ev .v { color:var(--txt); }
.ev .e.caret { color:var(--dim); }
.ev.hot .t, .ev.hot .e, .ev.hot .d, .ev.hot .k, .ev.hot .v { color:inherit; }

/* --- evidence --- */
.evhead { color:var(--dim); font-size:11px; margin:16px 0 8px 0;
          white-space:nowrap; overflow:hidden; }
.eline { font-size:13px; color:var(--txt); }
.eline .dim, .dim { color:var(--dim); }

/* --- findings --- */
table.findings { width:100%; border-collapse:collapse; font-size:13px; }
table.findings th {
  text-align:left; font-size:10px; letter-spacing:.14em; color:var(--dim);
  font-weight:400; border-bottom:1px solid var(--line); padding:0 8px 6px 0;
}
table.findings td { padding:6px 8px 6px 0; border-bottom:1px solid var(--line); vertical-align:top; }
table.findings td.meas { white-space:nowrap; font-variant-numeric:tabular-nums; }
table.findings td.sev { white-space:nowrap; }
table.findings tr.sev-action td:first-child {
  box-shadow:inset 2px 0 0 var(--action); padding-left:8px;
}

/* --- result --- */
.statusline { font-size:13px; color:var(--txt); margin:0 0 16px 0; }
.errline { font-size:13px; color:var(--txt); border-left:2px solid var(--action);
           padding-left:12px; margin:0 0 16px 0; }
.notassessed { font-size:12px; color:var(--dim); margin-top:12px; }
.traceid { font-size:11px; color:var(--faint); margin-top:16px; }
.empty { color:var(--faint); font-size:12px; }

/* --- the default Windows scrollbar is chunky enough to break the frame --- */
::-webkit-scrollbar { width:8px; height:8px; }
::-webkit-scrollbar-thumb { background:var(--line); }
::-webkit-scrollbar-track { background:transparent; }
</style>
"""

st.markdown(ROOT_VARS + THEME_CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------
# startup (cached so the embedding model and Ollama warm-up happen once)
# ----------------------------------------------------------------------

@st.cache_resource
def get_retriever():
    return Retriever()


@st.cache_resource
def warm_model():
    """One-token request so the first real run doesn't pay a cold start."""
    try:
        requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": "hi"}],
                "stream": False,
                "options": {"num_predict": 1},
            },
            timeout=30,
        )
    except Exception:
        pass
    return True


@st.cache_data
def corpus_stats():
    chunk_path = Path("data/index/chunks.pkl")
    if not chunk_path.exists():
        return 0, 0
    with open(chunk_path, "rb") as f:
        chunks = pickle.load(f)
    return len(chunks), len(set(c["doc"] for c in chunks))


def network_status():
    """Real check, not a label: try a 1s socket connect outward."""
    try:
        socket.setdefaulttimeout(1)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return "ONLINE"
    except OSError:
        return "OFFLINE"


try:
    retriever = get_retriever()
except Exception as exc:
    st.markdown(f"<div class='errline'>Could not load the retrieval index: "
                f"{html.escape(str(exc))}</div>", unsafe_allow_html=True)
    st.stop()

warm_model()


# ----------------------------------------------------------------------
# html builders  (single-line output: blank lines would trip the markdown parser)
# ----------------------------------------------------------------------

def pane_html(title, count=""):
    return (f"<div class='pane'><span>{html.escape(title)}</span>"
            f"<span class='count'>{html.escape(count)}</span></div>")


def status_bar_html(net, n_chunks, n_docs):
    net_color = "var(--ok)" if net == "OFFLINE" else "var(--alert)"
    cells = [
        ("MODEL", f"{MODEL} (local)", None),
        ("NETWORK", net, net_color),
        ("CORPUS", f"{n_chunks} chunks / {n_docs} docs", None),
        ("EXTERNAL CALLS", "0", None),
    ]
    out = []
    for label, value, color in cells:
        style = f" style='color:{color}'" if color else ""
        out.append(f"<span><span class='lbl'>{label}</span>"
                   f"<span class='val'{style}>{html.escape(value)}</span></span>")
    return "<div class='statusbar'>" + "".join(out) + "</div>"


def line_color(rec):
    """Colour only on refusal, validation, and errors. Nowhere else."""
    event = rec.get("event", "")
    if event == "refused":
        return "var(--action)"
    if event == "retrieval" and rec.get("refused"):
        return "var(--action)"
    if event == "artifact_validated":
        return "var(--ok)" if rec.get("valid") else "var(--action)"
    if event in ("artifact_invalid", "aborted"):
        return "var(--action)"
    return None


TRACE_SKIP = {"trace_id", "step", "ts", "elapsed_s", "event", "citations"}


def build_trace_html(records, running=False):
    if not records:
        return f"<div class='trace'><div class='empty'>{EMPTY}</div></div>"

    rows = []
    for rec in records:
        detail = " ".join(
            f"<span class='k'>{html.escape(str(k))}=</span>"
            f"<span class='v'>{html.escape(str(v))}</span>"
            for k, v in rec.items() if k not in TRACE_SKIP
        )
        color = line_color(rec)
        cls = "ev hot" if color else "ev"
        style = f" style='color:{color}'" if color else ""
        rows.append(
            f"<div class='{cls}'{style}>"
            f"<span class='t'>{rec.get('elapsed_s', 0.0):.2f}s</span>"
            f"<span class='e'>{html.escape(rec.get('event', ''))}</span>"
            f"<span class='d'>{detail}</span>"
            "</div>"
        )

    # Newest first: the container is column-reverse, so this renders oldest at the
    # top, newest at the bottom, pinned. One static caret while work is happening.
    body = "".join(reversed(rows))
    if running:
        caret = ("<div class='ev'><span class='t'></span>"
                 "<span class='e caret'>█</span><span class='d'></span></div>")
        body = caret + body
    return f"<div class='trace'>{body}</div>"


EVIDENCE_HEAD = "<div class='evhead'>── EVIDENCE USED " + "─" * 200 + "</div>"


def evidence_html(citations):
    if not citations:
        return f"<div class='empty'>{EMPTY}</div>"
    lines = []
    for c in citations:
        doc, _, page = c.partition(", ")
        page_html = f"<span class='dim'>, {html.escape(page)}</span>" if page else ""
        lines.append(f"<div class='eline'>{html.escape(doc)}{page_html}</div>")
    return "".join(lines)


def findings_table_html(findings):
    head = ("<tr><th>Parameter</th><th>Measured</th>"
            "<th>Severity</th><th>Source</th></tr>")
    rows = []
    for f in findings:
        sev = f["severity"]
        rows.append(
            f"<tr class='sev-{html.escape(sev)}'>"
            f"<td>{html.escape(f['parameter'])}</td>"
            f"<td class='meas'>{html.escape(f['measured_value'])}</td>"
            f"<td class='sev' style='color:{SEV_VAR.get(sev, 'var(--txt)')}'>"
            f"■ {html.escape(sev)}</td>"
            f"<td>{html.escape(f['source_doc'])}"
            f"<span class='dim'>, {html.escape(f['source_page'])}</span></td>"
            "</tr>"
        )
    return f"<table class='findings'>{head}{''.join(rows)}</table>"


def state_of(result, error):
    """The run-state line under the button."""
    if error:
        return "Error", "var(--action)"
    if result is None:
        return "Ready", "var(--dim)"
    if result["refused"]:
        return "Refused", "var(--action)"
    if result["reason"]:
        return "Stopped", "var(--action)"
    return f"Complete · {result['elapsed']}s", "var(--ok)"


# ----------------------------------------------------------------------
# session state
# ----------------------------------------------------------------------

st.session_state.setdefault("trace_records", [])
st.session_state.setdefault("evidence", [])
st.session_state.setdefault("result", None)
st.session_state.setdefault("error", None)


# ----------------------------------------------------------------------
# header
# ----------------------------------------------------------------------

n_chunks, n_docs = corpus_stats()

st.markdown("<div class='title'>Sovereign Workbench — SIH26117</div>",
            unsafe_allow_html=True)
st.markdown(status_bar_html(network_status(), n_chunks, n_docs),
            unsafe_allow_html=True)


# ----------------------------------------------------------------------
# layout
# ----------------------------------------------------------------------

left, right = st.columns([1, 2])

with left:
    st.markdown(pane_html("1. Task"), unsafe_allow_html=True)

    uploaded = st.file_uploader("Report", type=["pdf"])

    samples = sorted(SAMPLE_DIR.glob("*.pdf")) if SAMPLE_DIR.exists() else []
    sample_choice = st.selectbox("Sample", [NO_SAMPLE] + [s.name for s in samples])

    pdf_path = None
    if uploaded is not None:
        tmp_dir = Path(tempfile.gettempdir()) / "workbench_uploads"
        tmp_dir.mkdir(exist_ok=True)
        pdf_path = tmp_dir / uploaded.name
        pdf_path.write_bytes(uploaded.getvalue())
    elif sample_choice != NO_SAMPLE:
        pdf_path = SAMPLE_DIR / sample_choice

    request_text = st.text_area("Request", value=DEFAULT_REQUEST, height=100)

    run_clicked = st.button("Run", disabled=pdf_path is None, type="primary")
    state_box = st.empty()

    st.markdown("<hr class='rule'>", unsafe_allow_html=True)
    st.markdown(pane_html("3. Result"), unsafe_allow_html=True)
    result_box = st.container()

with right:
    trace_head = st.empty()
    trace_box = st.empty()
    st.markdown(EVIDENCE_HEAD, unsafe_allow_html=True)
    evidence_box = st.empty()


def render_trace(running=False):
    records = st.session_state.trace_records
    count = ""
    if records:
        count = f"{len(records)} events · {records[-1].get('elapsed_s', 0.0):.2f}s"
    trace_head.markdown(pane_html("2. Execution trace", count), unsafe_allow_html=True)
    trace_box.markdown(build_trace_html(records, running=running), unsafe_allow_html=True)
    evidence_box.markdown(evidence_html(st.session_state.evidence), unsafe_allow_html=True)


def render_state(label, color):
    state_box.markdown(f"<div class='runstate' style='color:{color}'>{html.escape(label)}</div>",
                       unsafe_allow_html=True)


render_trace()
render_state(*state_of(st.session_state.result, st.session_state.error))


# ----------------------------------------------------------------------
# run
# ----------------------------------------------------------------------

if run_clicked:
    st.session_state.trace_records = []
    st.session_state.evidence = []
    st.session_state.result = None
    st.session_state.error = None

    render_trace(running=True)
    render_state("Running", "var(--alert)")

    def on_event(rec):
        st.session_state.trace_records.append(rec)
        for c in rec.get("citations", []) or []:
            if c not in st.session_state.evidence:
                st.session_state.evidence.append(c)
        render_trace(running=True)

    try:
        st.session_state.result = run_agent(
            str(pdf_path), request_text, on_event=on_event, retriever=retriever
        )
    except CorruptPDFError:
        st.session_state.error = "Could not read this file. Is it a valid PDF?"
    except NoTextLayerError:
        st.session_state.error = ("No extractable text. This appears to be a scanned "
                                  "document; OCR is not yet implemented.")
    except requests.exceptions.ConnectionError:
        st.session_state.error = "Cannot reach Ollama at localhost:11434. Run 'ollama serve'."
    except Exception as exc:
        st.session_state.error = f"Unexpected error: {exc}"

    render_trace(running=False)
    render_state(*state_of(st.session_state.result, st.session_state.error))


# ----------------------------------------------------------------------
# pane 3 — result
# ----------------------------------------------------------------------

def render_result(result, error):
    if error:
        st.markdown(f"<div class='errline'>{html.escape(error)}</div>",
                    unsafe_allow_html=True)
        return

    if result is None:
        st.markdown(f"<div class='empty'>{EMPTY}</div>", unsafe_allow_html=True)
        return

    trace_id = (f"<div class='traceid'>Trace ID: "
                f"{html.escape(result['trace_id'])}</div>")

    # A refusal is a result, not a failure: same layout as any other outcome.
    if result["refused"] or result["reason"]:
        word = "Refused" if result["refused"] else "Stopped"
        body = (f"<div class='statusline'>"
                f"<span style='color:var(--action)'>{word}</span> — "
                f"{html.escape(result['reason'])}</div>")
        if result["unmatched"]:
            items = "".join(f"<div class='eline'>{html.escape(u)}</div>"
                            for u in result["unmatched"])
            body += ("<div class='notassessed'>No acceptance criterion matched:</div>"
                     + items)
        st.markdown(body + trace_id, unsafe_allow_html=True)
        return

    counts = result["counts"]
    tally = ", ".join(
        f"<span style='color:{SEV_VAR[s]}'>{counts[s]} {s}</span>"
        for s in ("action", "alert", "acceptable")
    )
    body = (f"<div class='statusline'><b>{html.escape(result['status'].replace('_', ' '))}"
            f"</b> — {tally}</div>"
            + findings_table_html(result["findings"]))

    if result["unmatched"]:
        body += ("<div class='notassessed'>Not assessed: "
                 + html.escape(", ".join(result["unmatched"])) + "</div>")

    st.markdown(body, unsafe_allow_html=True)

    out = result.get("out")
    if out and Path(out).exists():
        st.download_button(
            "Download .docx",
            data=Path(out).read_bytes(),
            file_name=Path(out).name,
            mime=("application/vnd.openxmlformats-officedocument"
                  ".wordprocessingml.document"),
        )

    st.markdown(trace_id, unsafe_allow_html=True)


with result_box:
    render_result(st.session_state.result, st.session_state.error)
