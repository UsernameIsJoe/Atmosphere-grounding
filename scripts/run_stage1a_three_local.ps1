# Run the three queued Stage 1A experiments locally on Windows PowerShell.
# Stage 1: five frozen real reviews; Stage 2: 214 real reviews;
# Stage 3: SetFit, 75 user-labeled training / 25 place-heldout evaluation.
# No synthetic source data. No LLM, Ollama, or CUDA required.
param(
    [switch] $SkipInstall
)
$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo
$python = Join-Path $repo ".venv-stage1a\Scripts\python.exe"
if (!(Test-Path $python)) {
    Write-Host "[SETUP] Creating isolated Python environment (.venv-stage1a)" -ForegroundColor Cyan
    py -3.11 -m venv .venv-stage1a
    if ($LASTEXITCODE -ne 0) { throw "Python 3.11 is required: py -3.11 -m venv .venv-stage1a" }
}
if (!$SkipInstall) {
    Write-Host "[SETUP] Installing runtime dependencies (first run downloads model packages)" -ForegroundColor Cyan
    & $python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
    & $python -m pip install "torch>=2.3,<3" "transformers>=4.45,<5" "setfit>=1.1,<2" "datasets>=2.18,<5" "sentence-transformers>=3,<6" "numpy>=1.26,<3" sentencepiece
    if ($LASTEXITCODE -ne 0) { throw "Python dependencies failed to install" }
}
Write-Host "[AUDIT] Verify all 100 user labels, exact source text and place split" -ForegroundColor Cyan
& $python scripts/stage1a_setfit_audit.py
if ($LASTEXITCODE -ne 0) { throw "Label or source audit failed. No inference will run." }
Write-Host "[1/3] Five-review frozen emotion-agnostic gate" -ForegroundColor Cyan
& $python scripts/stage1a_agnostic_gate.py --config configs/stage1a_evidence_first_5.json --output reports/stage1a_agnostic_gate_5_local
if ($LASTEXITCODE -ne 0) { throw "Five-review agnostic gate failed" }
Write-Host "[2/3] Full real-review corpus emotion-agnostic gate" -ForegroundColor Cyan
& $python scripts/stage1a_agnostic_gate.py --output reports/stage1a_agnostic_gate_full_local
if ($LASTEXITCODE -ne 0) { throw "Full-corpus agnostic gate failed" }
Write-Host "[3/3] SetFit training (75 user labels) and held-out scoring (25 labels)" -ForegroundColor Cyan
& $python scripts/stage1a_setfit_gate_train.py --out reports/stage1a_setfit_gate_local
if ($LASTEXITCODE -ne 0) { throw "SetFit training/evaluation failed; other output files remain available" }
Write-Host "SUCCESS: all 3 local experiments completed." -ForegroundColor Green
Write-Host "Results:" -ForegroundColor Green
Write-Host " reports/stage1a_agnostic_gate_5_local/{scores.jsonl,diagnostics.json}"
Write-Host " reports/stage1a_agnostic_gate_full_local/{scores.jsonl,diagnostics.json}"
Write-Host " reports/stage1a_setfit_gate_local/{heldout_predictions.jsonl,evaluation.json}"
Write-Host "To share the output in ChatGPT, compress these three directories into a ZIP and attach it."
