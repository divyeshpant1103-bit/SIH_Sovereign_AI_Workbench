# SIH26117 — Demo Setup Guide

**From empty machines to a working first-round demo.**

Follow this in order. Every step ends with a verification command and a "you are done when" line. Do not skip ahead — later steps assume earlier ones passed.

**Target:** a demo that films convincingly for the idea video and survives the internal round. Not a production system.

---

## Before you start

### What we already decided

| | |
|---|---|
| Demo machine | RTX 3050, dual-booted into Ubuntu 24.04 |
| Main model | Qwen2.5-3B-Instruct, 4-bit |
| Golden workflow | scanned inspection report → retrieve SOP clauses → compare → validated `.docx` |
| Non-negotiable | zero external calls, provable live |

### Machine roles

| Machine | OS | Runs |
|---|---|---|
| **RTX 3050** | Ubuntu 24.04, headless | Everything. Backend, agent, main model, sandbox, evidence stack |
| RTX 2050 | Windows | Vision model only (added day 13+) |
| GTX 1650 | Windows | Spare / vector store if needed |
| MacBook M1 | macOS | CPU work: embeddings, OCR (added day 13+) |

**Build everything to run on the 3050 alone first.** The other machines are enhancements added late. Four machines means four things that can fail the night before judging.

---

## Day 0 — Download everything (do this first, while online)

This is the most important day. Once you harden the machine, downloading gets painful. Grab everything now.

Do this on the 3050 **after** Ubuntu is installed (Day 1), or on any Ubuntu machine with the same architecture.

### 0.1 Create the cache structure

```bash
mkdir -p ~/sih-cache/{wheels,images,models,docs,apt}
cd ~/sih-cache
```

### 0.2 Python packages

Create `requirements.txt`:

```
# --- backend ---
fastapi==0.115.6
uvicorn[standard]==0.34.0
pydantic==2.10.4
python-multipart==0.0.20
structlog==24.4.0
tenacity==9.0.0
pyyaml==6.0.2

# --- model access ---
openai==1.59.6

# --- documents ---
docling==2.15.1
pymupdf==1.25.1
python-docx==1.1.2
docxtpl==0.19.0

# --- retrieval ---
lancedb==0.18.0
sentence-transformers==3.3.1
rank-bm25==0.2.2
FlagEmbedding==1.3.3

# --- classifier ---
scikit-learn==1.6.0
numpy==2.2.1

# --- ocr (cpu) ---
paddlepaddle==2.6.2
paddleocr==2.9.1

# --- dev ---
pytest==8.3.4
httpx==0.28.1
```

Download them:

```bash
python3.11 -m pip download -r requirements.txt -d ~/sih-cache/wheels/
```

> **Note on versions:** pin them. An unpinned install on demo day that pulls a breaking change is a self-inflicted wound. If a version fails to resolve, bump it and re-pin, don't remove the pin.

### 0.3 Models

```bash
# after Ollama is installed (step 2.1)
ollama pull qwen2.5:3b-instruct-q4_K_M
ollama pull qwen2.5-coder:3b
ollama pull qwen2.5vl:3b          # vision, for day 13+
```

Verify the exact tag names first at `ollama.com/library` — tags change. `ollama list` shows what you actually have.

Back them up:

```bash
sudo tar -czf ~/sih-cache/models/ollama-models.tar.gz \
  -C /usr/share/ollama/.ollama models
```

### 0.4 Embedding and OCR models

These download from Hugging Face on first use. Trigger them once now:

```bash
python3.11 -c "
from sentence_transformers import SentenceTransformer
SentenceTransformer('BAAI/bge-m3')
SentenceTransformer('BAAI/bge-small-en-v1.5')
"

python3.11 -c "
from paddleocr import PaddleOCR
PaddleOCR(use_angle_cls=True, lang='en')
"
```

Then archive the caches:

```bash
tar -czf ~/sih-cache/models/hf-cache.tar.gz -C ~ .cache/huggingface
tar -czf ~/sih-cache/models/paddle-cache.tar.gz -C ~ .paddleocr
```

Docling also downloads layout models on first run — run it once on a sample PDF before archiving.

### 0.5 Docker images

```bash
docker pull python:3.11-slim
docker save python:3.11-slim -o ~/sih-cache/images/python311.tar
```

### 0.6 Demo documents

You need ~15 public documents. **Do not use copyrighted standards** (ASME, API, IS codes are not freely redistributable). Use these instead — all genuinely industrial, all freely available:

| Source | What to grab |
|---|---|
| **US DOE Handbooks** (DOE-HDBK series) | Mechanical Science, Instrumentation and Control, Chemistry. Public domain, real engineering content, excellent for this |
| **OSHA** Process Safety Management | 1910.119 guidance documents |
| **NIOSH** | Pocket guide, chemical safety cards |
| **EPA** Risk Management Program | Guidance for petroleum refineries |
| **IAEA** safety standards | Freely downloadable, procedure-heavy |
| Manufacturer manuals | Pump, valve, heat exchanger manuals published openly by vendors |

Save into `~/sih-cache/docs/`.

**You also need 3–4 scanned inspection reports.** Write these yourself:
1. Type a realistic inspection report in Word (equipment tag, date, inspector, measured values, observations).
2. Print it.
3. Photograph or scan it, slightly crooked, on a phone.

This gives you a genuine scan you fully control, with a known correct answer. Make one of them contain a deliberate deviation from a procedure in your corpus — that's your demo.

### 0.7 Verify

```bash
du -sh ~/sih-cache/*
```

**Done when:** wheels, images, models and docs directories all have content, and total size is several GB.

---

## Day 1 — Ubuntu on the RTX 3050

Budget a full day. The graphics driver is the part that goes wrong.

### 1.1 Before you touch anything

- Back up anything important on that machine.
- Note your Windows BitLocker recovery key if it's enabled.
- In Windows: disable Fast Startup (Control Panel → Power Options → Choose what the power buttons do).
- Shrink the Windows partition to free at least 100 GB (Disk Management → Shrink Volume).

### 1.2 Install

1. Download Ubuntu 24.04.x LTS Desktop ISO.
2. Write it to USB with Rufus or `dd`.
3. Boot with Secure Boot **disabled** in BIOS (simplifies driver install).
4. Choose "Install Ubuntu alongside Windows Boot Manager".
5. Allocate the free space.

### 1.3 NVIDIA driver

```bash
sudo apt update && sudo apt upgrade -y
sudo ubuntu-drivers devices          # shows recommended driver
sudo ubuntu-drivers install
sudo reboot
```

Verify:

```bash
nvidia-smi
```

**Done when:** `nvidia-smi` prints a table showing your RTX 3050 and its 4096 MiB. Write down the "Memory-Usage" figure at idle — that's your overhead.

### 1.4 Go headless (recovers ~500 MB VRAM)

Do this after you've confirmed everything works with a desktop:

```bash
sudo systemctl set-default multi-user.target
sudo reboot
```

You now get a text console. Work over SSH from another laptop:

```bash
sudo apt install -y openssh-server
ip addr show          # note the IP
```

To get the desktop back temporarily: `sudo systemctl set-default graphical.target`

Check the gain:

```bash
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

**Done when:** idle VRAM usage is under ~150 MiB.

### 1.5 Base packages

```bash
sudo apt install -y \
  build-essential git curl wget \
  python3.11 python3.11-venv python3.11-dev \
  nftables bpfcc-tools linux-headers-$(uname -r) \
  poppler-utils tesseract-ocr
```

### 1.6 Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
docker run --rm hello-world
```

**Done when:** `hello-world` prints its message without `sudo`.

---

## Day 2 — Ollama and your first benchmark

### 2.1 Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2.2 Configure it for our hardware

```bash
sudo systemctl edit ollama.service
```

Add:

```ini
[Service]
Environment="OLLAMA_HOST=127.0.0.1:11434"
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
Environment="OLLAMA_KEEP_ALIVE=30m"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

`MAX_LOADED_MODELS=1` because two 3B models will not fit in 4 GB. `KV_CACHE_TYPE=q8_0` roughly halves working memory. Flash attention is required for the KV cache setting to apply.

### 2.3 Pull the model

```bash
ollama pull qwen2.5:3b-instruct-q4_K_M
ollama list
```

### 2.4 Set context properly

Ollama defaults to a small context. With retrieved documents injected, that will silently truncate your evidence. Create a Modelfile:

```bash
cat > /tmp/Modelfile <<'EOF'
FROM qwen2.5:3b-instruct-q4_K_M
PARAMETER num_ctx 8192
PARAMETER temperature 0.1
EOF

ollama create workbench-general -f /tmp/Modelfile
```

Use `workbench-general` everywhere from now on.

### 2.5 Benchmark — record these numbers

```bash
ollama run workbench-general --verbose "Explain in exactly three sentences what a pressure relief valve does."
```

Note the reported eval rate (tokens/second). Then:

```bash
nvidia-smi --query-gpu=memory.used --format=csv    # while loaded
```

Create `docs/benchmarks.md` in your repo and write down:

```
Machine: RTX 3050 4GB laptop, Ubuntu 24.04 headless
Model: qwen2.5:3b-instruct-q4_K_M, num_ctx 8192, KV q8_0
Tokens/sec: ___
VRAM loaded: ___ MiB
Cold load time: ___ s
Date: ___
```

**Do this again with Q5_K_M** if it fits, and compare. Recent research shows 4-bit quantization degrades noticeably on long-context tasks — and RAG is a long-context task. If Q5 fits in 3.4 GB, the quality may be worth the extra memory. Measure, don't assume.

### 2.6 Prove localhost needs no internet

```bash
sudo nmcli networking off
curl http://localhost:11434/api/tags
ollama run workbench-general "Say OK."
sudo nmcli networking on
```

**Done when:** both worked with networking off. Record this — it's your first evidence.

---

## Day 3 — Repository skeleton

### 3.1 Structure

```bash
mkdir -p ~/mrpl-workbench/{services/{models,agent,tools,rag,vision,evidence},apps/web,infra,data/{samples,index},eval,docs,scripts}
cd ~/mrpl-workbench && git init
```

### 3.2 Virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --no-index --find-links=$HOME/sih-cache/wheels -r requirements.txt
```

Using `--no-index` proves your offline cache actually works. If it fails now, better than on demo day.

### 3.3 Offline environment flags

Create `infra/offline.env`:

```bash
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
export ANONYMIZED_TELEMETRY=False
export DO_NOT_TRACK=1
export SCARF_NO_ANALYTICS=true
export OLLAMA_HOST=127.0.0.1:11434
export TOKENIZERS_PARALLELISM=false
```

Source it in every shell. Add to `~/.bashrc`.

> **This is the most likely way our sovereignty claim fails.** Standard AI libraries check for updates and send usage statistics without telling you. Ten minutes here prevents an unrecoverable embarrassment.

### 3.4 The four foundation files

Write these **together, in one sitting**. They are the contract every other person codes against.

| File | Contains |
|---|---|
| `services/agent/schemas.py` | Pydantic models: `TaskRequest`, `TaskPlan`, `ToolCall`, `Evidence`, `Finding`, `FindingSet` |
| `services/tools/base.py` | The `Tool` protocol: name, args schema, `run()` returning a structured result |
| `services/models/adapter.py` | `ModelAdapter` with `generate()` and `generate_structured()` |
| `services/evidence/trace.py` | `Trace.emit()` appending one JSON line per event |

After these exist, everyone works independently.

### 3.5 The fake adapter

Also write `services/models/fake.py` returning fixed responses. Your agent developer can then build and test the entire executor with no GPU. Keep it afterwards as a regression test.

**Done when:** `python -c "from services.agent.schemas import TaskPlan; print(TaskPlan.model_json_schema())"` prints a schema.

---

## Days 4–6 — Retrieval, with citations

The knowledge layer has no AI in it. It's pure search. Build and test it independently.

### 4.1 Ingestion pipeline

`services/rag/ingest.py` does, in order:

1. For each PDF, check the text layer: if `chars_per_page < 100`, mark as scanned.
2. Born-digital → PyMuPDF direct extraction.
3. Scanned → PaddleOCR (leave this stubbed until Day 13 if you want; start with born-digital only).
4. Docling for structure: headings, sections, tables.
5. Chunk by section, 400–800 tokens, ~15% overlap.
6. Attach metadata to every chunk: `doc_id`, `page`, `section_path`, `source_path`, `bbox`.
7. Embed with BGE-M3 **on CPU**.
8. Write to LanceDB.

### 4.2 Search pipeline

`services/rag/search.py`:

1. Embed the query (CPU).
2. Dense search in LanceDB → top 50.
3. BM25 keyword search → top 50.
4. Merge with Reciprocal Rank Fusion (k=60).
5. Rerank with BGE-reranker → top 5.
6. If top score < threshold, return `insufficient_evidence`.

Hybrid matters here: refinery documents are full of equipment tags and standard codes that must match exactly, which meaning-based search alone will miss.

### 4.3 The golden set

Create `eval/golden.jsonl` — 30 to 50 questions with known answers:

```json
{"q": "What is the minimum wall thickness for the pump casing?", "doc": "DOE-HDBK-1018", "page": 47, "answer_contains": "6.4 mm"}
{"q": "What colour is the sky on Mars?", "doc": null, "expect": "refusal"}
```

Include 5–8 unanswerable questions. **The refusal path is a feature you will demo deliberately.**

### 4.4 Measure

`eval/run_retrieval.py` reports recall@5 and citation accuracy. Write the numbers into `docs/benchmarks.md`.

**Done when:** you can ask a question, get the right paragraph with a correct page number, and get a clean refusal on an unanswerable one.

---

## Days 7–9 — Agent and the Word document

### 7.1 Tools

Build five, each behind the `Tool` protocol from Day 3:

| Tool | Notes |
|---|---|
| `kb.search` | wraps the Day 4–6 search |
| `file.read` | workspace paths only, no traversal |
| `file.write` | workspace paths only |
| `calc.verify` | deterministic calculation |
| `doc.generate` | fills the Word template |

### 7.2 The executor

`services/agent/executor.py` implements: retrieve → check evidence → plan once → execute steps → analyse → generate → validate.

Two AI calls per task, not eight. Retrieval, tool execution and document generation involve no model at all.

Hard limits, all enforced in one `Budget` object:

```
max_steps      = 8
max_repairs    = 2
wall_clock     = 180 s
per_tool_timeout = 30 s
```

Plus a loop guard: hash `(tool_name, canonical_args)`; a repeated hash aborts immediately.

### 7.3 The Word template

Make `data/templates/approval_note.docx` in Word with `docxtpl` placeholders:

```
Equipment: {{ equipment_tag }}
Inspection date: {{ inspection_date }}

{% for f in findings %}
{{ loop.index }}. {{ f.description }}
   Reference: {{ f.source_doc }}, page {{ f.source_page }}
{% endfor %}
```

The model fills a `FindingSet`; `docxtpl` renders it. **The model never writes document code.**

### 7.4 Validation

After generating, reopen with `python-docx` and assert: file opens, required sections present, every finding carries a source reference. Log `artifact_valid: true/false`.

**Done when:** one full run produces a `.docx` that opens in Word with correct citations.

---

## Days 10–12 — The evidence stack

This is your differentiator. Two days, highest value per hour of anything in the project.

### 10.1 Firewall

`/etc/nftables.conf`:

```
table inet filter {
  chain output {
    type filter hook output priority 0; policy drop;
    oif "lo" accept
    ip daddr 172.16.0.0/12 accept
    ip daddr 192.168.0.0/16 accept
    ct state established,related accept
    log prefix "EGRESS-BLOCKED: " counter drop
  }
}
```

```bash
sudo systemctl enable --now nftables
sudo nft list ruleset
sudo nft list counters
```

> Add SSH access rules **before** enabling this if you're working remotely, or you will lock yourself out.

### 10.2 Kernel connection monitor

```bash
sudo tcpconnect-bpfcc
```

This prints PID, process name, destination IP and port for every outbound connection attempt. Pipe it into a collector that writes to your event log. **This is the money shot** — a judge sees attempted connections with process attribution.

Fallback if bcc gives trouble:

```bash
sudo tcpdump -i any -n 'not net 172.16.0.0/12 and not net 192.168.0.0/16 and not host 127.0.0.1'
```

### 10.3 Sandbox

`infra/sandbox.yml`:

```yaml
services:
  sandbox:
    image: python:3.11-slim
    network_mode: none
    read_only: true
    tmpfs: [/tmp:size=64m]
    mem_limit: 512m
    cpus: 1.0
    pids_limit: 64
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    user: "65534:65534"
```

Test that it genuinely has no network:

```bash
docker run --rm --network none python:3.11-slim \
  python -c "import socket; socket.create_connection(('1.1.1.1',53),timeout=3)"
```

**Done when:** that command fails with a network error.

### 10.4 The contrast demo

Run a deliberately unhardened script (no offline env vars) with the monitor on. Capture what it tries to contact. Then run the hardened version showing nothing. Screenshot both. This contrast is worth more than any architecture diagram.

### 10.5 DNS logging (optional, do last)

`dnsmasq` conflicts with `systemd-resolved` on port 53. Only attempt this once everything else is stable, and know how to revert.

**Done when:** you can run the full workflow with the cable unplugged and show a live counter reading zero external connections.

---

## Days 13–15 — Vision, routing, and the other machines

### 13.1 Scanned document path

Enable the PaddleOCR branch in ingestion. Test on your photographed inspection reports.

### 13.2 The classifier

Write ~200 labelled example requests. Train a logistic regression over `bge-small` embeddings:

```
document_qa | report_review | code_calc | vision_extract
```

Under 10 ms, deterministic, cannot invent a category. Save with joblib.

### 13.3 Router

`infra/models.yaml`:

```yaml
models:
  general:
    base_url: http://localhost:11434/v1
    model_id: workbench-general
    status: approved
  coder:
    base_url: http://localhost:11434/v1
    model_id: qwen2.5-coder:3b
    status: approved
  vision:
    base_url: http://192.168.1.42:11434/v1
    model_id: qwen2.5vl:3b
    status: approved
```

Every routing decision emits `model_selected` with its reason into the trace.

### 13.4 Second machine

On the RTX 2050 (Windows): install Ollama, set `OLLAMA_HOST=0.0.0.0:11434`, pull the vision model. Confirm from the 3050:

```bash
curl http://192.168.1.42:11434/api/tags
```

Handle the node being down gracefully — catch the connection error, emit `node_down`, fall back to OCR-only. Never let one laptop's power settings kill the demo.

**Done when:** the UI visibly routes a document task and a vision task to different models, with reasons shown.

---

## Days 16–18 — Interface and hardening

### 16.1 Three panes

**Task** (input and status) · **Trace & Evidence** (default view) · **Artifacts** (generated files).

The trace pane streams events as they happen. **Never show a spinner** — the workflow takes 60–90 seconds, which feels endless when frozen and short when steps appear live.

### 16.2 Failure testing

Deliberately break things and confirm graceful behaviour:

- Unplug the vision node mid-task
- Feed a corrupt PDF
- Ask an unanswerable question
- Make a tool time out
- Fill the disk

### 16.3 The golden replay

Record one perfect run's event log. Build a replay mode that streams it. If the live demo misbehaves, you switch to replay and keep talking. Say it's a recording if asked — being caught pretending is far worse than admitting a backup.

---

## Days 19–21 — Submission package

- [ ] Demo video, multiple takes
- [ ] Idea PPT with architecture diagram
- [ ] Measured numbers slide (real figures only)
- [ ] Honest limitations slide
- [ ] The cable-unplug shot, filmed clearly
- [ ] Side-by-side of hardened vs unhardened network capture
- [ ] README with setup instructions

---

## Verification checklist

Run before any demo:

```bash
# 1. Offline inference
sudo nmcli networking off
ollama run workbench-general "Say OK." && echo "PASS"

# 2. Firewall active
sudo nft list ruleset | grep -q "policy drop" && echo "PASS"

# 3. Sandbox has no network
docker run --rm --network none python:3.11-slim \
  python -c "import socket; socket.create_connection(('1.1.1.1',53),timeout=2)" \
  2>/dev/null || echo "PASS"

# 4. Full workflow
python -m eval.run_golden_workflow && echo "PASS"

sudo nmcli networking on
```

All four must pass.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Model OOMs on load | Context too large | Lower `num_ctx` to 4096; confirm headless |
| Model ignores your documents | Context silently truncating | You forgot `num_ctx` in the Modelfile |
| First query takes 25 s | Cold model load | Prewarm at backend startup with a 1-token request |
| Locked out over SSH after nftables | No SSH accept rule | Console access, `sudo nft flush ruleset`, add rule, retry |
| `tcpconnect-bpfcc` errors | Missing kernel headers | `sudo apt install linux-headers-$(uname -r)` and reboot |
| Docling downloads at runtime | Cache not warmed | Run once online, archive `~/.cache`, set `HF_HUB_OFFLINE=1` |
| 404 from Ollama | Wrong model tag | `ollama list` for exact names |
| PaddleOCR install fails on Python 3.12 | Version incompatibility | Use Python 3.11 |
| Nothing works after `nmcli networking off` | Something needs a real network | Good — you found a leak. Find it in the trace and fix it |

---

## This week, in order

1. **Ubuntu on the 3050.** Blocks everything else. Start today.
2. **Day 0 downloads.** Do this the moment Ubuntu boots.
3. **Ollama benchmark.** One number in a file beats a week of speculation.
4. **The four foundation files**, written together as a team.
5. **Collect the 15 documents** and photograph your fake inspection reports.

Report back with: tokens/sec on the 3050, MacBook memory (`system_profiler SPHardwareDataType | grep Memory`), and the college lab's GPU model.

---

## The rule

Before adding anything, ask: **does this make the golden workflow more reliable, more measurable, or more provably offline?**

If not, it goes on the roadmap slide, not into the code.