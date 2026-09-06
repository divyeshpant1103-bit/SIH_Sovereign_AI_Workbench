# Streamlit UI — Visual Spec

Companion to `SIH26117_Streamlit_UI_Spec.md`. That document decided **what is on screen**. This one decides **how it looks**. Nothing here changes agent behaviour, the trace contract, or the `.docx`.

**Goal:** stop looking like an untouched Streamlit demo and start looking like an instrument. Same three panes, same omissions, same argument — better executed.

Budget: ~60 minutes. Two files touched: `.streamlit/config.toml` (new) and `app.py` (one CSS constant, three render functions).

---

## The argument, restated

The original rule was "default theme, because polish reads as ChatGPT wrapper." That rule was aimed at the right target and hit the wrong one. Default Streamlit does not read as *neutral*; it reads as *unfinished*, and its own chrome (rainbow decoration bar, Deploy button, rounded cards) reads as **web app**, which is the second-worst thing we can look like.

A terminal aesthetic is not decoration. It is the same argument the trace makes, carried by the typography:

| Default Streamlit says | A console says |
|---|---|
| a data app someone deployed | a program running on this machine |
| generic SaaS surface | an internal tool with an operator |
| rounded, soft, consumer | fixed-width, aligned, instrumented |

We are not making it *pretty*. We are making it *look like what it is*. Every rule below is still minimal — one typeface, one grid, four colours, no ornament. Minimalism is a discipline, not an absence of decisions.

---

## The rules

1. **One typeface.** Monospace everywhere, including headings and buttons. No mixing.
2. **Colour carries meaning only.** Severity, network status, and nothing else. Everything else is a value on one grey ramp.
3. **Hairlines, not boxes.** 1px borders. No cards, no shadows, no elevation, no fills.
4. **Square corners.** Radius 0 everywhere.
5. **One alignment grid.** Every left edge in a column lines up. Every number is right-aligned and tabular.
6. **No motion.** The trace streaming is the only thing that moves, and it moves because work is happening.
7. **Nothing loads from the network.** Non-negotiable — see Typeface.

---

## Palette

Dark is the default. Values are the GitHub dark ramp, which is already tuned for legibility on projectors and colour-deficient vision.

| Role | Token | Hex | Notes |
|---|---|---|---|
| Background | `--bg` | `#0B0C0E` | Near-black, very slightly cool. Not `#000` |
| Panel / inputs | `--bg2` | `#15171B` | Text areas, uploader, selectbox |
| Hairline | `--line` | `#262A31` | Every border and divider |
| Text | `--txt` | `#D8DEE6` | Not pure white; pure white vibrates on near-black |
| Dim | `--dim` | `#8A929E` | Labels, payload keys, secondary values |
| Faint | `--faint` | `#5A616B` | Empty states, `=` glyphs, placeholder |
| Action | `--action` | `#F85149` | Severity only |
| Alert | `--alert` | `#E3B341` | Severity, and `ONLINE` network state |
| Acceptable | `--ok` | `#3FB950` | Severity, and `OFFLINE` network state |

Contrast on `--bg`: text 12.6:1, dim 6.1:1, action 5.4:1, alert 10.7:1, ok 7.9:1. All above 4.5:1. Faint is 3.2:1 and is therefore only ever used on text that carries no information.

**Red/amber/green is the worst case for deuteranopia.** Colour is never the only encoding — every severity prints its word (`action`, `alert`, `acceptable`) next to the swatch, and action rows carry a left border bar. If a judge asks, that is the answer, and it is a real one.

**Paper variant.** If the room is bright or the projector is weak, invert rather than compromise. Note the pleasing symmetry: the light palette's severity colours are already in the codebase — they are the `.docx` colours in `agent.py`.

| Role | Hex |
|---|---|
| `--bg` / `--bg2` / `--line` | `#FAFAF8` / `#F2F2EE` / `#E0E0DA` |
| `--txt` / `--dim` / `--faint` | `#1B1D21` / `#5F666F` / `#8A9098` |
| action / alert / ok | `#A8501E` / `#B8860B` / `#2E6B3E` |

Decide which at rehearsal, in the actual room, and then leave it. It is one config file. **Still no toggle in the UI.**

---

## Typeface

### The constraint nobody thinks about

**No web fonts.** A `fonts.googleapis.com` request is a real external call. It would contradict the `External calls: 0` counter sitting in our own header, it would hang for seconds on an air-gapped machine, and it is exactly the thing a sharp judge would catch. The font ships with the machine or ships with the repo. There is no third option.

### Stack (recommended — zero risk)

```
"Cascadia Mono", "Cascadia Code", "JetBrains Mono", Consolas, "Courier New", monospace
```

Cascadia ships with Windows 11 and Windows Terminal and is the best-looking of these; Consolas is on every Windows since Vista and is the guaranteed floor. Confirm which one actually resolves on the demo machine before the day — see Verify.

### Bundling JetBrains Mono (optional, ~10 min, nicer)

If you want the distinct look, bundle it. It is OFL-licensed, so shipping the file is fine.

1. Drop `JetBrainsMono-Regular.woff2` and `JetBrainsMono-Bold.woff2` into `static/` at the repo root.
2. Enable Streamlit's local static serving in `config.toml` (`[server] enableStaticServing = true`); files are then served from `/app/static/…` — same origin, same machine, no network.
3. Declare it in the CSS block:

```css
@font-face {
  font-family: "JetBrains Mono";
  src: url("app/static/JetBrainsMono-Regular.woff2") format("woff2");
  font-weight: 400; font-display: block;
}
```

Streamlit 1.63 also accepts `[[theme.fontFaces]]` entries in config, which is tidier — confirm the exact key names with `streamlit config show` before relying on it. Either way it stays local.

### Scale

Monospace runs small; do not go below these on a 1080p projector.

| Element | Size | Weight | Treatment |
|---|---|---|---|
| Page title | 15px | 700 | Sentence case, `--txt` |
| Status bar label | 10px | 400 | UPPERCASE, `letter-spacing: .14em`, `--dim` |
| Status bar value | 12px | 400 | `--txt`, or severity colour for network |
| Pane header | 11px | 700 | UPPERCASE, `letter-spacing: .14em`, `--dim`, hairline under |
| Widget label | 10px | 400 | UPPERCASE, `letter-spacing: .14em`, `--dim` |
| Body / table | 13px | 400 | — |
| Trace line | 13px | 400 | `line-height: 1.55`, tabular numerals |
| Button | 12px | 700 | UPPERCASE, `letter-spacing: .1em` |

Spacing scale: **4 / 8 / 16 / 24 / 32**. Nothing in between, nothing outside it. Column gap 32. Section gap 24. Table row padding 6/8.

---

## `.streamlit/config.toml`

New file. This does most of the work — it themes the *widgets* correctly, which CSS cannot do cleanly.

```toml
[theme]
base                    = "dark"
backgroundColor         = "#0B0C0E"
secondaryBackgroundColor = "#15171B"
textColor               = "#D8DEE6"
primaryColor            = "#D8DEE6"   # monochrome accent: RUN reads as a key, not a CTA
borderColor             = "#262A31"
linkColor               = "#8A929E"
baseRadius              = "none"      # square corners everywhere
baseFontSize            = 13
font                    = '"Cascadia Mono", "JetBrains Mono", Consolas, monospace'
headingFont             = '"Cascadia Mono", "JetBrains Mono", Consolas, monospace'
codeFont                = '"Cascadia Mono", "JetBrains Mono", Consolas, monospace'

[client]
toolbarMode = "minimal"    # kills the Deploy button and most of the hamburger

[server]
enableStaticServing = true # only needed if bundling a font
headless = true            # no auto-open, no email prompt on first run
```

`primaryColor` set to the text white is deliberate: Streamlit paints the primary button and focus rings with it, so **RUN** becomes a light key with dark text — the highest-contrast object on screen, which is correct, since it is the only thing to press. It also keeps colour meaning-only.

> Streamlit warns on unrecognised config keys at startup. If a key above is rejected on 1.63, drop that line — none of them are load-bearing.

---

## CSS block

One constant at the top of `app.py`, injected once. Target `data-testid` attributes only — Streamlit's generated class names change between versions, `data-testid` is stable.

```python
THEME_CSS = """
<style>
:root {
  --bg:#0B0C0E; --bg2:#15171B; --line:#262A31;
  --txt:#D8DEE6; --dim:#8A929E; --faint:#5A616B;
  --action:#F85149; --alert:#E3B341; --ok:#3FB950;
}

/* --- kill Streamlit's own branding chrome --- */
[data-testid="stDecoration"] { display:none; }        /* the rainbow gradient strip */
[data-testid="stToolbar"] { display:none; }           /* Deploy + hamburger */
[data-testid="stStatusWidget"] { display:none; }      /* the running indicator: the trace is the indicator */
[data-testid="stHeader"] { background:transparent; height:0; }

/* --- page frame --- */
.stMainBlockContainer, .block-container {
  padding: 24px 32px 32px 32px; max-width: 1600px;
}
[data-testid="stVerticalBlockBorderWrapper"] { background:transparent; }

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

/* --- RUN --- */
.stButton > button {
  width:100%; border-radius:0; font-weight:700;
  letter-spacing:.1em; text-transform:uppercase;
}

/* --- vertical hairline between the task column and the trace --- */
[data-testid="stColumn"]:last-child { border-left:1px solid var(--line); padding-left:32px; }

/* --- pane headers --- */
.pane {
  font-size:11px; font-weight:700; letter-spacing:.14em; text-transform:uppercase;
  color:var(--dim); border-bottom:1px solid var(--line);
  padding-bottom:6px; margin:0 0 16px 0;
  display:flex; justify-content:space-between; align-items:baseline;
}
.pane .count { font-weight:400; color:var(--faint); letter-spacing:.06em; }

/* --- status bar --- */
.statusbar { display:flex; gap:32px; flex-wrap:wrap; align-items:baseline;
             border-top:1px solid var(--line); border-bottom:1px solid var(--line);
             padding:10px 0; margin-bottom:24px; }
.statusbar .lbl { font-size:10px; letter-spacing:.14em; color:var(--dim); margin-right:8px; }
.statusbar .val { font-size:12px; color:var(--txt); font-variant-numeric:tabular-nums; }

/* --- trace --- */
.trace {
  height:calc(100vh - 340px); min-height:420px; overflow-y:auto;
  display:flex; flex-direction:column-reverse; justify-content:flex-end;
  font-size:13px; line-height:1.55; font-variant-numeric:tabular-nums;
}
.ev { display:grid; grid-template-columns:5rem 14rem 1fr; gap:12px; padding:1px 0; }
.ev .t { color:var(--dim); text-align:right; }
.ev .e { color:var(--txt); }
.ev .d { color:var(--dim); word-break:break-word; }
.ev .k { color:var(--faint); }
.ev .v { color:var(--txt); }
.ev.hot .t, .ev.hot .e, .ev.hot .d, .ev.hot .k, .ev.hot .v { color:inherit; }

/* --- findings table --- */
table.findings { width:100%; border-collapse:collapse; font-size:13px; }
table.findings th {
  text-align:left; font-size:10px; letter-spacing:.14em; color:var(--dim);
  font-weight:400; border-bottom:1px solid var(--line); padding:0 8px 6px 0;
}
table.findings td { padding:6px 8px 6px 0; border-bottom:1px solid var(--line); vertical-align:top; }
table.findings td.meas { white-space:nowrap; font-variant-numeric:tabular-nums; }
table.findings td.sev  { white-space:nowrap; }
table.findings tr.sev-action td:first-child { box-shadow:inset 2px 0 0 var(--action); padding-left:8px; }
.dim { color:var(--dim); }
.empty { color:var(--faint); font-size:12px; }

/* --- thin scrollbars; the default Windows bar is chunky and breaks the frame --- */
::-webkit-scrollbar { width:8px; height:8px; }
::-webkit-scrollbar-thumb { background:var(--line); }
::-webkit-scrollbar-track { background:transparent; }
</style>
"""
```

> Two or three of those selectors may need a nudge once you inspect the real DOM on 1.63. Check them in devtools; anything that misses simply leaves that element unstyled, it does not break the app.

---

## What is actually wrong right now, and the fix

| # | Defect in `app.py` today | Fix |
|---|---|---|
| 1 | Header spaced with `&nbsp;&nbsp;&nbsp;&nbsp;` — ragged, doesn't align | Flex row, `gap:32px`, label/value pairs |
| 2 | Heading levels `####` / `#####` picked arbitrarily | The type scale above; panes become `.pane` micro-headers |
| 3 | Findings table built from one `st.columns()` **per row** — each row is its own block with default padding, so the rows breathe unevenly and never form a table | One HTML `<table>`, rendered in a single markdown call |
| 4 | Trace lines joined with `<br>` + `white-space:pre-wrap` — a long `detail` wraps back to column 0 and destroys the timestamp gutter | CSS grid per line; wrapped detail hangs inside its own column |
| 5 | Trace pane grows without bound — the page gets taller mid-run and the Result pane drifts down the screen while judges are watching | Fixed-height scroll viewport |
| 6 | No separation between the two columns | 1px vertical hairline |
| 7 | `st.divider()` carries heavy default margins | Hairline with 16/24 margins |
| 8 | ~6rem of dead space above the header in wide mode | `padding-top:24px` |
| 9 | Widget labels inconsistent in voice and case (`Upload PDF`, `...or pick a sample report`, `Request`) | `REPORT` / `SAMPLE` / `REQUEST` — uppercase micro-labels |
| 10 | Empty states differ (`No run yet.` vs `_none yet_`) | One voice, one style: `awaiting task` in `--faint` |
| 11 | Streamlit's gradient decoration bar and **Deploy** button are visible — a credibility leak in the first second | Hidden via config + CSS |
| 12 | Everything is rounded | `baseRadius = "none"` |

---

## Trace pane

The heart of it, and where the remaining polish budget goes.

### Two-tone payloads

The single highest-impact change in this document. A log where keys are dim and values are bright reads as *designed*; a log in one colour reads as *dumped*.

```python
def build_trace_html(records):
    if not records:
        return "<div class='trace'><span class='empty'>awaiting task</span></div>"

    skip = {"trace_id", "step", "ts", "elapsed_s", "event", "citations"}
    rows = []
    for rec in records:
        detail = " ".join(
            f"<span class='k'>{html.escape(str(k))}=</span>"
            f"<span class='v'>{html.escape(str(v))}</span>"
            for k, v in rec.items() if k not in skip
        )
        color = line_color(rec)                       # unchanged logic
        cls = "ev hot" if color else "ev"
        style = f" style='color:{color}'" if color else ""
        rows.append(
            f"<div class='{cls}'{style}>"
            f"<span class='t'>{rec.get('elapsed_s', 0.0):.2f}s</span>"
            f"<span class='e'>{html.escape(rec.get('event',''))}</span>"
            f"<span class='d'>{detail}</span>"
            f"</div>"
        )
    # reversed: the container is column-reverse, which pins the view to the newest line
    return "<div class='trace'>" + "".join(reversed(rows)) + "</div>"
```

Note `.ev.hot` in the CSS: when a row carries a severity colour, its children must inherit it rather than keep their own greys.

### Sticking to the bottom, without JavaScript

We re-render the whole placeholder on every event, so scroll position resets to the top and the newest line — the one being talked about on stage — scrolls out of view. `st.markdown` strips `<script>`, so the usual `scrollIntoView` is not available.

CSS solves it: `flex-direction: column-reverse` on the scroll container, rows fed in reverse order. The view stays pinned to the newest line while streaming, and the operator can still scroll back. `justify-content: flex-end` keeps the first few events at the *top* of the box instead of floating at the bottom of an empty panel.

If that misbehaves, the fallback is `st.components.v1.html` (an iframe, which does allow a script) with the styles inlined. Do not spend more than 15 minutes on this.

### Pane header carries the count

```
EXECUTION TRACE                          13 events · 42.03s
```

Free instrumentation, and it gives the presenter a number to land on when the run finishes.

### Evidence block

Keep the box-drawing separator the original mock drew — it costs nothing and is beautiful in monospace:

```
── EVIDENCE USED ──────────────────────────────
DOE-HDBK-1018-1-93, ME-03 p.12
DOE-HDBK-1018-1-93, ME-03 p.16
SOP-PMP-114-limits, Section 2
```

Document bright, `, page` dim. One per line, deduplicated, as specified.

---

## Findings table

```python
def findings_table_html(findings):
    head = ("<tr><th>PARAMETER</th><th>MEASURED</th>"
            "<th>SEVERITY</th><th>SOURCE</th></tr>")
    rows = []
    for f in findings:
        sev = f["severity"]
        rows.append(
            f"<tr class='sev-{sev}'>"
            f"<td>{html.escape(f['parameter'])}</td>"
            f"<td class='meas'>{html.escape(f['measured_value'])}</td>"
            f"<td class='sev' style='color:var(--{SEV_VAR[sev]})'>■ {sev}</td>"
            f"<td>{html.escape(f['source_doc'])}"
            f"<span class='dim'>, {html.escape(f['source_page'])}</span></td>"
            "</tr>"
        )
    return f"<table class='findings'>{head}{''.join(rows)}</table>"
```

`■` is a geometric character, not an emoji — it inherits text colour and renders identically everywhere. Action rows also carry the left border bar from the CSS, so the four action findings are findable from the back of the room without reading a word.

---

## Status bar

```
MODEL  workbench (local)    NETWORK  OFFLINE    CORPUS  176 chunks / 3 docs    EXTERNAL CALLS  0
```

Labels dim, uppercase, letter-spaced. Values bright, tabular. `OFFLINE` in `--ok`, `ONLINE` in `--alert`, unchanged from the original spec. Hairline above and below, 24px clear beneath.

## Run state

One line directly under the RUN button. It is the only status text on the screen, and it replaces the spinner we are not allowed to have:

| State | Shows | Colour |
|---|---|---|
| idle | `READY` | `--dim` |
| running | `RUNNING` | `--alert` |
| finished | `COMPLETE · 42.0s` | `--ok` |
| refused | `REFUSED` | `--action` |
| failed | `ERROR` | `--action` |

---

## Additions worth making

Everything above is remediation. These are the things I would add, in value order:

1. **Two-tone trace payloads** — biggest single visual gain per line of code.
2. **Fixed trace viewport with bottom-pinning** — stops the layout dancing during the run. This one is really a correctness fix wearing a design hat.
3. **Event count + elapsed in the pane header** — instrumentation, and a number to say out loud.
4. **Run-state line** — replaces the forbidden spinner honestly.
5. **Tabular numerals everywhere** (`font-variant-numeric: tabular-nums`) — the elapsed column becomes a clean rule down the left of the trace. One CSS line.
6. **Left border bar on action rows** — severity findable at a glance, no new colour introduced.
7. **Hide the Streamlit toolbar, decoration bar, and status widget** — the Deploy button alone can cost us the "this is an internal tool" read.
8. **Set the browser tab** — `page_title="Sovereign Workbench"` is already set; the favicon is still Streamlit's logo, which is visible every time the presenter alt-tabs. A 32×32 local PNG fixes it. Five minutes, no emoji.
9. **Thin scrollbars** — the default Windows scrollbar is chunky enough to break the frame.
10. **A single static caret `█` at the tail of the trace while running** — optional, one only, and **it does not blink**. A blinking cursor on a projector is a distraction that reads as costume. If you want it, this is the one piece of terminal theatre that earns its place.

---

## What stays out

| Not doing | Why |
|---|---|
| CRT scanlines, glow, bloom, phosphor green | Costume, not craft. Instantly reads as a theme someone downloaded |
| Character-by-character typewriter animation | The trace already streams at real speed. Faking latency is lying about the system's behaviour, in the one pane whose entire job is honesty |
| Blinking anything (except the optional single caret, which doesn't) | Distraction on a projector |
| ASCII-art banner / figlet title | One step from a logo, which is already excluded |
| Web fonts over the network | Would contradict `External calls: 0`. See Typeface |
| Dark/light toggle | Still no. Decide in the room, ship one |
| Cards, shadows, elevation, gradients | Hairlines only |
| Icon library, emoji | Geometric characters where a mark is needed |
| Restyling `st.dataframe` internals | Chasing Streamlit's internal DOM. We render our own table instead |
| Charts | Unchanged from the original spec: eight findings, not a dataset |

---

## Risk and fallback

Every visual change lives in two places: `.streamlit/config.toml` and one `THEME_CSS` constant. **Delete either and the app still runs**, unstyled but fully functional. No render path depends on a selector matching. That property is the reason this is safe to do the week of a demo, and it should stay true — if a change to `app.py` cannot be reverted by deleting a style block, it does not belong in this document.

Pin the Streamlit version (1.63.0) before the demo. `data-testid` values are stable, but there is no reason to find out otherwise on the day.

---

## Order of work

| Min | Do | Gain |
|---|---|---|
| 0–15 | `config.toml`: colours, radius, font stack, `toolbarMode` | ~60% of the total gain. Do this first, stop here if time runs out |
| 15–25 | CSS block: chrome hiding, pane headers, hairlines, inputs, button | Fixes 1, 2, 6, 7, 8, 11, 12 |
| 25–45 | Trace rewrite: grid, two-tone, viewport, bottom-pinning | Fixes 4, 5; additions 1, 2, 5 |
| 45–55 | Findings table as HTML; status bar; run-state line | Fixes 3, 9, 10; additions 3, 4, 6 |
| 55–60 | Favicon, scrollbars, empty-state copy | Additions 8, 9 |

Optional font bundling is a separate 10 minutes and should be done last, or not at all.

---

## Done when

Load the app with no run yet and check, in order:

- [ ] No rainbow strip, no **Deploy** button, no Streamlit hamburger, no running-man indicator
- [ ] Everything is monospace, including the button and the headings
- [ ] The status bar aligns on one line with even gaps; `OFFLINE` is the only green thing on screen
- [ ] Both panes' left edges align to the same grid; a hairline separates the columns
- [ ] Trace pane reads `awaiting task` in faint grey and is already at its full height

Then run `INS-2026-0847` and check:

- [ ] The page does not change height or jump while the trace streams
- [ ] Elapsed times form a clean right-aligned column; keys dim, values bright
- [ ] The newest line stays visible without touching the scrollbar
- [ ] `artifact_validated` is the only green line; a refusal, when it happens, is the only red one
- [ ] Findings read as one table with even rows, and the four action rows are identifiable from three metres away
- [ ] `COMPLETE · 42.0s` under the button, trace ID in faint at the bottom of the Result pane

Then `INS-2026-0863` and confirm the refusal still reads as a **result**, styled in `--action` but laid out like every other outcome — not as an error state.

---

## Verify on the machine

Three checks, five minutes, worth doing before you write any code:

```powershell
streamlit config show          # confirms which theme keys 1.63 actually accepts
```

- In the browser, devtools → Computed → `font-family` on a trace line. Confirm it resolved to Cascadia and not the `monospace` fallback.
- Project it. Dark themes are where weak projectors go to die; if `--dim` text is unreadable on the wall, switch to the paper variant rather than lifting the greys one at a time.
