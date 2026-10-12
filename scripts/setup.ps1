$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
py -3 scripts/bootstrap_check.py
if ($LASTEXITCODE -ne 0) { throw "Storage/Python check refused installation" }
py -3 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
& .\.venv\Scripts\python.exe -m pip install --no-cache-dir -e ".[test]"
if ($LASTEXITCODE -ne 0) { throw "dependency installation failed" }
& .\.venv\Scripts\python.exe -m fullstackops doctor
