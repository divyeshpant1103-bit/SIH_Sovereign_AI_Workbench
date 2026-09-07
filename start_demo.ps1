# start_demo.ps1
# Pre-flight and launcher for the SIH26117 demo.
#
# Run this instead of starting Streamlit by hand. It checks everything,
# warms both models so there is no cold-start pause during the demo, and
# then opens the interface.
#
#   powershell -ExecutionPolicy Bypass -File start_demo.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

function Say($msg)  { Write-Host "  $msg" -ForegroundColor Gray }
function Ok($msg)   { Write-Host "  OK   $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "  ..   $msg" -ForegroundColor Yellow }
function Die($msg)  { Write-Host "  FAIL $msg" -ForegroundColor Red; Read-Host "`nPress Enter to exit"; exit 1 }

Write-Host ""
Write-Host "  SOVEREIGN WORKBENCH - PRE-FLIGHT" -ForegroundColor Cyan
Write-Host "  ================================" -ForegroundColor Cyan
Write-Host ""

$sw = [System.Diagnostics.Stopwatch]::StartNew()

# ----------------------------------------------------------------
# 1. offline environment flags
# ----------------------------------------------------------------
$env:HF_HUB_OFFLINE        = "1"
$env:TRANSFORMERS_OFFLINE  = "1"
$env:HF_DATASETS_OFFLINE   = "1"
$env:ANONYMIZED_TELEMETRY  = "False"
$env:DO_NOT_TRACK          = "1"
$env:SCARF_NO_ANALYTICS    = "true"
$env:TOKENIZERS_PARALLELISM = "false"
$env:OLLAMA_HOST           = "127.0.0.1:11434"
Ok "Offline flags set (no library will phone home)"

# ----------------------------------------------------------------
# 2. project files
# ----------------------------------------------------------------
if (-not (Test-Path ".\.venv\Scripts\python.exe")) { Die "No virtual environment at .venv" }
if (-not (Test-Path ".\app.py"))                   { Die "app.py not found" }
if (-not (Test-Path ".\data\index\vectors.npy"))   { Die "No search index. Run: python ingest.py" }

$chunks = (Get-Item ".\data\index\chunks.pkl").Length
Ok "Project files present (index $([math]::Round($chunks/1KB)) KB)"

$py = ".\.venv\Scripts\python.exe"

# ----------------------------------------------------------------
# 3. Ollama
# ----------------------------------------------------------------
function Test-Ollama {
    try {
        $r = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3
        return $r
    } catch { return $null }
}

$tags = Test-Ollama
if ($null -eq $tags) {
    Warn "Ollama not running, starting it"
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 500
        $tags = Test-Ollama
        if ($tags) { break }
    }
    if ($null -eq $tags) { Die "Ollama would not start. Try 'ollama serve' manually." }
}
Ok "Ollama responding on localhost:11434"

$names = $tags.models | ForEach-Object { $_.name }
if (-not ($names -match "workbench")) {
    Die "Model 'workbench' not found. Run: ollama create workbench -f Modelfile"
}
Ok "Model 'workbench' available"

# ----------------------------------------------------------------
# 4. warm the language model  (this is the 25 second cold start)
# ----------------------------------------------------------------
Say "Warming language model, please wait"
$t = [System.Diagnostics.Stopwatch]::StartNew()
$body = @{ model = "workbench"; prompt = "hi"; stream = $false;
           keep_alive = "60m" } | ConvertTo-Json
try {
    Invoke-RestMethod -Uri "http://localhost:11434/api/generate" -Method Post `
        -Body $body -ContentType "application/json" -TimeoutSec 120 | Out-Null
} catch { Die "Model warm-up failed: $_" }
Ok "Language model warm and resident ($([math]::Round($t.Elapsed.TotalSeconds,1))s)"

# ----------------------------------------------------------------
# 5. warm the embedding model  (this is the 10 second pause mid-run)
# ----------------------------------------------------------------
Say "Warming embedding model"
$t = [System.Diagnostics.Stopwatch]::StartNew()
$warm = @"
from search import Retriever
r = Retriever()
r.search('warm up query')
print('embeddings ready')
"@
$warm | & $py - 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Warn "Embedding warm-up had a problem, continuing anyway" }
else { Ok "Embedding model warm ($([math]::Round($t.Elapsed.TotalSeconds,1))s)" }

# ----------------------------------------------------------------
# 6. network status, for information
# ----------------------------------------------------------------
$online = Test-Connection -ComputerName 8.8.8.8 -Count 1 -Quiet -ErrorAction SilentlyContinue
if ($online) {
    Write-Host "  ..   Network is ONLINE - turn on airplane mode before demonstrating" -ForegroundColor Yellow
} else {
    Ok "Network is OFFLINE"
}

# ----------------------------------------------------------------
# 7. launch
# ----------------------------------------------------------------
Write-Host ""
Write-Host "  Ready in $([math]::Round($sw.Elapsed.TotalSeconds,1))s. Opening interface." -ForegroundColor Cyan
Write-Host "  Close this window to stop the demo." -ForegroundColor Gray
Write-Host ""

& ".\.venv\Scripts\streamlit.exe" run app.py