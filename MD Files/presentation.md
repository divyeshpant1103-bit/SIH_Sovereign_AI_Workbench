# SIH26117 — Round 1 Idea PPT Content

**Template constraints:** 6 slides max including title. Points/diagrams only, no paragraphs. Delete the instructions slide. Export as PDF.

**What wins this round:** almost every team submits an idea. You will submit an idea *plus a screenshot of it running*. Put that screenshot on Slide 3. It changes how everything else is read.

---

## Slide 1 — Title Page

Fill the existing fields exactly:

```
Problem Statement ID –  SIH26117
Problem Statement Title- Sovereign On-Premise Agentic AI Workbench using
                         Open-Weight Multimodal LLMs for Confidential Industrial Work
Theme- Smart Automation
PS Category- Software
Team ID- <from portal>
Team Name- <registered name>
```
---

## Slide 2 — Proposed Solution

**Title placeholder:** `KAVACH — The AI Workbench That Can Prove It Never Called Home`

Lay this out as three columns. Keep every bullet under 12 words.

### Column 1 — What it is

- A **private AI operating layer**, not a chatbot
- Runs entirely on the organisation's own GPU server
- Takes a **job**, returns a **finished file** — not a chat reply
- Open-weight models, downloaded once, swappable later

### Column 2 — How it solves the problem

- Confidential documents never leave the perimeter
- Answers grounded in MRPL's own manuals, cited to **document + page**
- Multi-step work automated: read → retrieve → compare → draft → verify
- Creates an **approved path** for AI, replacing shadow AI use

### Column 3 — Innovation & uniqueness

- **Sovereignty is measured, not claimed** — kernel-level proof of zero egress
- **Bounded agent**: plans once, executes under hard step/time limits
- **Refuses to answer** when evidence is weak — a feature, not a failure
- **Signed offline model import** — updates without ever connecting
- **Audit trail is the product**, not a log file

### Bottom strip — the golden workflow

Render as a single horizontal arrow chain:

```
Scanned inspection report → OCR + parse → retrieve SOP clauses (cited)
→ compare findings vs. criteria → validate evidence coverage
→ generate approval note .docx → show trace + zero-egress proof
```

### Speaker note

> "Our differentiator isn't that the model runs locally — anyone can do that. It's that we can prove nothing left, at the kernel level, while a judge watches."

---

## Slide 3 — Technical Approach

Split the slide: left half technologies, right half the flow diagram plus your prototype screenshot.

### Technologies (left, grouped — not a flat list)

| Layer | Stack |
|---|---|
| **Inference** | Ollama / llama.cpp · Qwen2.5-3B-Instruct · Qwen2.5-Coder · Qwen2.5-VL · GGUF Q4_K_M |
| **Retrieval** | Docling · PyMuPDF · BGE-M3 embeddings · LanceDB · BM25 hybrid + RRF · BGE reranker |
| **Vision** | PaddleOCR PP-Structure (CPU) · vision-language model for figures only |
| **Agent** | Custom Python state machine · Pydantic schemas · schema-constrained decoding |
| **Output** | python-docx · docxtpl templates · automated file validation |
| **Isolation** | nftables · Docker `network_mode: none` · eBPF (bcc-tools) · dnsmasq |
| **Platform** | FastAPI · React · Docker Compose · Ubuntu 24.04 |

Add one line underneath, in bold:

> **Every component open-source, offline-capable, and replaceable — model independence is a design requirement, not a claim.**

### Flow diagram (right)

Nine boxes, top to bottom, with the two proof callouts on the side:

```
1  User task + file upload
2  Ingestion (once): parse → OCR if needed → chunk → embed → index
3  Classifier: document / code / vision          [sklearn, <10 ms]
4  Router: selects model + logs reason           ← ROUTING PROOF
5  Hybrid retrieval → rerank → cited evidence
   └─ weak evidence? → REFUSE
6  Agent: plan once → execute (max 8 steps, 3 min)
7  Structured findings (schema-constrained JSON)
8  Deterministic .docx generation → validate
9  Trace + evidence + egress counter             ← SOVEREIGNTY PROOF
```

### The screenshot

Bottom-right corner: your running prototype showing the trace panel mid-execution, ideally with the egress counter reading zero. Caption it:

> *Working prototype — inspection report → cited comparison → validated .docx, executed with networking disabled.*

### Two design decisions worth one line each

- **Vision runs at ingestion, not in the agent loop** — keeps response time usable on constrained GPUs
- **The model writes structured data; deterministic code writes the file** — output is reliable, not usually-fine

---

## Slide 4 — Feasibility and Viability

This is where you win against teams that overclaim. Use a three-column risk table. Judges test for honesty here more than anywhere else.

### Feasibility — already demonstrated

- Working prototype running on a **4 GB consumer GPU**
- Measured: `___ tokens/sec` · `___ s end-to-end` · `___ MB VRAM` *(fill from your benchmark)*
- Full workflow completes with **networking physically disabled**
- Every component is free, open-source and offline-capable — **zero licensing cost**
- PS explicitly permits smaller models where 120B-class hardware is unavailable

### Challenges and mitigations

| Challenge | Why it's real | Our mitigation |
|---|---|---|
| Limited GPU memory | 4 GB cards can't hold multiple models | 4-bit quantisation, quantised KV cache, sequential loading, one model per node |
| 4-bit accuracy loss on long context | Documented in recent literature — up to 59% drop on long inputs | Reranking to top-5 keeps context tight; Q4 vs Q5 benchmarked on our golden set |
| Model hallucination | Wrong findings in an approval note are dangerous | Mandatory citations, refusal threshold, human approval gate before use |
| Agent loops or wrong actions | Known failure mode for small open models (AgentBench) | Plan-once execution, 8-step cap, 3-min budget, repeat-action abort |
| Generated code is unsafe | An LLM wrote it; treat it as hostile | Container with no network namespace, dropped capabilities, memory/PID/time limits |
| Offline model updates | Air-gap makes patching harder, not optional | Signed bundles, hash + licence + malware checks, eval gate before approval |
| Engineering drawings (P&IDs) | Open VLMs invent component labels | Scoped out honestly; needs a dedicated symbol detector — stated as roadmap |
| Our own libraries phone home | HF update checks, telemetry — the real leak | Offline env flags, and we *show* the blocked attempts as evidence |

### Viability

- Runs on hardware most PSUs already own; no new procurement to pilot
- Fits MRPL's existing ISO 27001 data-centre posture rather than bypassing it
- No per-token cost, no rate limits, no vendor deprecating your model
- Same architecture scales from one laptop to a multi-GPU server unchanged

---

## Slide 5 — Impact and Benefits

**Do not put invented percentages on this slide.** No public MRPL baseline exists, and a judge asking "where did 40% come from" ends badly. Frame impact as capability unlocked.

### Target audience

- **Primary:** MRPL engineers, inspection, procurement, finance, project teams
- **Extends to:** refineries, PSUs, defence-linked manufacturing, government offices

### Impact

| Today | With KAVACH |
|---|---|
| Sensitive work done manually, or pasted into public AI | An approved internal path — shadow AI risk removed |
| Manuals and SOPs searched by hand across systems | Cited retrieval with document and page reference |
| Scanned reports read and compared manually | Structured extraction and automated comparison |
| Approval notes drafted from scratch each time | Grounded draft generated, reviewed by a human |
| Nothing to show IT/security about AI usage | Full audit trail: sources, tools, model, network evidence |

### Benefits

- **Security** — confidential data provably never leaves the perimeter
- **Trust** — every claim traceable to a source page; system refuses rather than guesses
- **Governance** — auditable record makes AI usable under regulated conditions
- **Economic** — one-time hardware cost, no recurring API spend, no rate limits
- **Strategic** — model independence protects against vendor and roadmap lock-in
- **National** — a reusable pattern for any Indian organisation that cannot use cloud AI

### The honest line that earns credibility

> "We are not claiming a productivity percentage. No public baseline exists. What we claim is measured: the workflow completes offline, every answer is cited, and zero external calls occur."

---

## Slide 6 — Research and References

Group them. A flat list of fifteen links looks padded; grouped references look like a literature review.

### Problem definition
- SIH 2026 Problem Statement SIH26117 (MRPL) — sih.gov.in
- MRPL Annual Reports 2020-21, 2022-23, 2023-24 — digital transformation, SAP S/4HANA, ISO 27001 data centre
- MRPL R&D disclosures — deployed AI/ML in plant operations

### Retrieval and grounding
- Lewis et al., *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* — arXiv:2005.11401
- Gao et al., *RAG for LLMs: A Survey* — arXiv:2312.10997
- Liu et al., *Lost in the Middle* — arXiv:2307.03172
- Es et al., *RAGAS* — arXiv:2309.15217

### Agents and tool use
- Yao et al., *ReAct* — arXiv:2210.03629
- Schick et al., *Toolformer* — arXiv:2302.04761
- Liu et al., *AgentBench* — arXiv:2308.03688 *(basis for our bounded-agent design)*
- Singh et al., *Agentic RAG: A Survey* — arXiv:2501.09136

### Deployment under hardware constraints
- Dettmers & Zettlemoyer, *k-bit Inference Scaling Laws* — arXiv:2212.09720
- *Does quantization affect long-context performance?* — arXiv:2505.20276 *(directly informed our Q4/Q5 benchmark)*
- Liu et al., *Task-Aware LLM Routing (TRouter)* — arXiv:2604.09377

### Document understanding
- *OmniDocBench* — arXiv:2412.07626
- *When Good OCR Is Not Enough: OCR Robustness for RAG* — arXiv:2605.00911

### Isolation and execution security
- *SandboxEval* — arXiv:2504.00018
- Docker — none network driver / `network_mode: none`
- NIST AI RMF 1.0 + Generative AI Profile (NIST.AI.600-1)

### Existing platforms reviewed
- Azure OpenAI private endpoints · Amazon Bedrock PrivateLink · Red Hat OpenShift AI disconnected · NVIDIA NIM air-gap deployment · IndiaAI Mission (MeitY 2025-26)

Add one closing line:

> **Reviewed as alternatives — each solves part of the problem; none covers air-gap + multi-model + multimodal + agents + local tools + organisational RAG + deliverables + verifiable zero-egress as one system.**

---

## Delete Slide 7

The template says so explicitly.

---

## Design notes

- **13.33 × 7.5 inches, 16:9.** Don't resize.
- Keep the team-name oval and SIH logo on every slide.
- **Minimum 16pt body text.** If it doesn't fit, cut words, don't shrink type.
- Two visuals minimum: the flow diagram (Slide 3) and the prototype screenshot (Slide 3).
- Colour: one accent throughout. Deep teal or navy. No gradients, no clip art.
- Export as **PDF**. The portal rejects .pptx.

---

## Four things to avoid

1. **"Nothing like this exists."** False at the component level and easy to disprove. Say "no single product covers this combination" instead.
2. **Invented metrics.** Any percentage you can't source is a liability.
3. **A screenshot of a chat interface.** It reframes you as a ChatGPT wrapper. Show the trace panel.
4. **Listing ten models.** Three used well beats a model zoo. Judges read a long model list as inexperience.

---

## The one-line test

If a judge reads only your Slide 2 tagline and Slide 3 screenshot, do they understand that you built something that works offline and can prove it?

If yes, the deck is done.
