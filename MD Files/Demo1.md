# SIH26117 — 3-Day Prototype Plan

**Single laptop. GTX 1650 4GB. Windows. No dual boot.**

Round-1 college demo only. Everything cut that isn't visible in a 5-minute presentation.

---

## The scope cut

| Building | Cutting |
|---|---|
| Local model running offline | Multi-laptop cluster |
| RAG with page citations | Vector database (numpy is enough for 500 chunks) |
| Refusal when evidence is weak | Reranker |
| Agent producing a real `.docx` | Code sandbox / code execution |
| Visible model routing (2 models) | OCR and vision (optional stretch) |
| Airplane-mode offline proof | eBPF, nftables, dnsmasq |
| Live trace panel | React frontend (Streamlit instead) |

**Demo scenario:** typed inspection report PDF in → retrieve matching SOP clauses → compare → approval note `.docx` out → all with the wifi off.

No OCR. Type your fake inspection report in Word and export as PDF. Say honestly that the scanned-document pipeline is built for the finale.

---

## Day 1 — Environment and retrieval (~10 hours)

### 1.1 Install (45 min)

- **Ollama for Windows** — download the installer from ollama.com, run it. Done.
- **Python 3.11** — python.org installer. Tick "Add to PATH". Not 3.12, some packages lag.

```powershell
ollama --version
python --version
```

### 1.2 Model (30 min)

```powershell
ollama pull qwen2.5:3b-instruct-q4_K_M
ollama pull qwen2.5-coder:1.5b
```

Why 3B and not 1.5B for the main model: the 1.5B is noticeably worse at following a JSON schema and writing a coherent plan, which is exactly what you need it for. 2.0 GB fits comfortably in 4 GB.

Set the context properly — this is the trap that wastes an afternoon:

```powershell
@"
FROM qwen2.5:3b-instruct-q4_K_M
PARAMETER num_ctx 8192
PARAMETER temperature 0.1
"@ | Out-File -Encoding ascii Modelfile

ollama create workbench -f Modelfile
```

Ollama's default context is small. Without this, your retrieved documents get silently truncated and the model appears to ignore evidence you know you gave it.

### 1.3 Benchmark and offline proof (30 min)

```powershell
ollama run workbench --verbose "Explain in three sentences what a pressure relief valve does."
```

Write down the tokens/sec. On a 1650 expect roughly 20–35 depending on whether yours has GDDR5 or GDDR6. Prompt processing is slower than generation on this card since Turing has no tensor cores, so budget 3–6 seconds before text starts appearing with a full context.

Then turn on **airplane mode** and run it again. Screenshot it. That's your first piece of evidence and it took two minutes.

### 1.4 Python environment (30 min)

```powershell
mkdir workbench; cd workbench
python -m venv .venv
.venv\Scripts\activate
pip install ollama fastapi uvicorn streamlit pymupdf sentence-transformers rank-bm25 python-docx numpy pydantic
```

Warm the embedding model cache while you still have internet:

```powershell
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"
```

`bge-small` is 66 MB and runs on CPU. Not `bge-m3` — that's 2 GB and you don't need it for eight documents.

### 1.5 Documents (1 hour)

Grab 6–8 public PDFs. **US DOE Handbooks** (DOE-HDBK series: Mechanical Science, Instrumentation and Control) are ideal — public domain, genuinely industrial, procedure-heavy. Add OSHA process safety guidance.

Avoid ASME and API standards. Copyrighted, not redistributable, and you don't want that question at judging.

Then write **one fake inspection report** in Word. Equipment tag, date, inspector name, measured values, observations. Make one measured value deliberately violate a limit stated in one of your DOE documents. Export as PDF. That single file is your entire demo.

### 1.6 Ingestion (2 hours)

One script, `ingest.py`:

1. PyMuPDF extracts text page by page.
2. Split into ~600-word chunks with 15% overlap.
3. Store `{text, doc_name, page, chunk_id}`.
4. Embed all chunks with `bge-small` on CPU.
5. Pickle the chunk list and a numpy array of embeddings.

**No vector database.** For a few hundred chunks, `numpy.dot` is faster than any database and removes a whole category of setup problems.

### 1.7 Retrieval (2 hours)

`search.py`:

1. Embed the query.
2. Cosine similarity against the array → top 20.
3. BM25 keyword scores via `rank_bm25` → top 20.
4. Merge with reciprocal rank fusion → top 5.
5. **If the best score is below a threshold, return `insufficient_evidence`.**

Hybrid matters here because refinery text is full of equipment tags and codes that meaning-based search alone misses.

### 1.8 Test (1 hour)

Write 10 questions with known answers plus 3 unanswerable ones. Confirm you get right pages and clean refusals.

**Day 1 done when:** you ask a question in a terminal and get the correct paragraph with a document name and page number.

---

## Day 2 — Agent and Word output (~10 hours)

### 2.1 The two-call flow (3 hours)

Do **not** build a ReAct loop. Two model calls total:

```
1. search(request)                    → evidence + page refs      [no model]
2. if weak evidence → refuse                                      [no model]
3. model call 1: extract findings from the report as JSON
4. model call 2: compare findings against evidence, output FindingSet as JSON
5. render docx from FindingSet                                    [no model]
6. reopen and validate                                            [no model]
```

Two calls at ~10 seconds each is 20 seconds. A loop would be eight calls and 90 seconds, and would occasionally hang.

Force valid JSON using Ollama's `format` parameter with a Pydantic schema. The model then physically cannot produce malformed output, which matters enormously on a 3B model.

### 2.2 Word generation (2 hours)

`python-docx` directly. Heading, equipment details, numbered findings, each with `Source: {doc}, page {n}`, then a recommendation line.

**The model never writes document code.** It fills a `FindingSet`; your code builds the file. Then reopen it with `python-docx` and assert the required sections exist.

### 2.3 Routing (45 min)

Keyword rule, 20 lines:

```
"calculate" / "compute" / "script" / "code"  → qwen2.5-coder:1.5b
everything else                              → workbench
```

Log the decision and the reason. This satisfies the automatic model selection requirement visibly, and you can show it in the UI. Don't over-build it.

### 2.4 Streamlit UI (3 hours)

Three sections top to bottom:

1. **Task** — file uploader and a text box
2. **Live trace** — events appearing as they happen
3. **Result** — download button for the `.docx`

Make the trace the visual centre, not a chat box. Use `st.status` and `st.expander`. Every event: task received, classified, model selected + reason, 4 sources retrieved (with page numbers), findings extracted, document generated, validation passed.

**Stream it.** Never a spinner. Twenty seconds of visible progress feels fast; twenty seconds of a frozen screen feels broken.

### 2.5 Trace log (1 hour)

Append one JSON line per event to `trace.jsonl`. Streamlit reads it. This is both your debug tool and the thing you show the judges.

**Day 2 done when:** upload the inspection report, click run, watch the trace fill, download a `.docx` that opens in Word with correct citations.

---

## Day 3 — Proof, polish, rehearsal (~8 hours)

### 3.1 Offline evidence (2 hours)

Four things, all Windows-native:

**Airplane mode.** Toggle it on, run the whole workflow, film it. This is the demo moment.

**Firewall rule.** Create an outbound block rule for python.exe in Windows Defender Firewall with Advanced Security. Screenshot the rule.

**netstat.** Run `netstat -bn` during a task, show no external connections. A running counter of "external connections: 0" in the UI is even better if you have time.

**The contrast.** Set the offline environment variables:

```powershell
$env:HF_HUB_OFFLINE=1
$env:TRANSFORMERS_OFFLINE=1
$env:ANONYMIZED_TELEMETRY="False"
$env:DO_NOT_TRACK=1
```

Run once *without* them and capture what your own libraries try to contact — Hugging Face update checks, telemetry endpoints. Then show your hardened version contacting nothing. That side-by-side is your strongest single slide and it costs 30 minutes.

### 3.2 Break it deliberately (1 hour)

- Unanswerable question → clean refusal, demo this on purpose
- Corrupt PDF → error message, no crash
- Empty upload → handled

### 3.3 Record the backup (1 hour)

Film one perfect run, screen and audio. If the live demo misbehaves you switch to the recording and keep talking. Say it's a recording if asked. Being caught pretending is far worse than admitting a backup.

### 3.4 Slides (2 hours)

Six slides, no more:

1. The problem — confidential work can't go to cloud AI
2. What we built — one sentence plus the workflow diagram
3. Live demo
4. How we prove zero egress — the four layers
5. Measured numbers — your actual tokens/sec, retrieval accuracy, end-to-end time
6. Roadmap — Linux migration with kernel monitoring, OCR pipeline, multi-model cluster, sandbox

### 3.5 Rehearse (2 hours)

Full run, out loud, three times. Everyone should be able to run it alone. Judges ask whoever is nearest, not whoever wrote that part.

---

## What to say about the cuts

Don't hide them. Frame each as sequenced:

> "Today's prototype runs the complete workflow on one machine. The document pipeline handles born-digital PDFs; OCR for scanned pages is next. Isolation is proved at the OS and application layer; we're migrating to Linux for kernel-level connection monitoring with process attribution. Model routing works across two models on one GPU; the architecture supports separate inference nodes without code changes."

That reads as a plan. "We ran out of time" reads as a plan that failed.

---

## The one thing that must work

**Upload the inspection report, get a valid Word document, with the wifi off.**

If day three arrives and something has to go, cut the routing, cut the second model, cut the trace polish. Do not cut that sentence.
