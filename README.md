# FullStackOps-30M

A working, storage-bounded Python dataset builder for Priyan's coding LLM / DevOps agent project.
**30M is the long-term target. This release contains a measured 1,000-record pilot.**

The pilot contains 875 original configuration-policy repairs and 125 original Python arithmetic repairs,
across 63 families. The Python tasks execute finite trusted expressions with actual baseline/fault/fix evidence.
The policy checks parse YAML and compare a required value. They do not build Docker images, start services,
provision cloud resources, or validate full Kubernetes/Terraform schemas.

## Windows PowerShell quick start

Install Python 3.11 or newer. Extract this ZIP, then open PowerShell in `FullStackOps-30M`:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -e ".[test]"
.\.venv\Scripts\python.exe -m fullstackops doctor
.\.venv\Scripts\python.exe -m fullstackops validate
.\.venv\Scripts\python.exe -m pytest -q
```

The included `data/` is already the completed pilot, so `resume` verifies its checkpoints and retains 1,000 records.
To reproduce from zero, copy `config/settings.yaml` to `config/reproduce.yaml`, change `workspace: data` to
`workspace: data-reproduced`, then run:

```powershell
.\.venv\Scripts\python.exe -m fullstackops --config config/reproduce.yaml build --limit 1000
.\.venv\Scripts\python.exe -m fullstackops --config config/reproduce.yaml validate
```

`--config` goes BEFORE the subcommand. No activation or execution-policy change is required.
You can also run `scripts/setup.ps1`; it checks a conservative 1 GiB installation allowance first.
Windows commands are provided, but this delivery was tested on Linux, not on a physical Windows laptop.

## Linux / macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --no-cache-dir -e '.[test]'
.venv/bin/python -m fullstackops doctor
.venv/bin/python -m fullstackops validate
```

## Commands

| Command | Actual behavior |
| --- | --- |
| `doctor` | OS/Python, free disk, RAM, budgets, upload configuration |
| `init` | Owned workspace directories and WAL-mode SQLite state |
| `generate --limit 1000` | Original finite pilot tasks, validation and Parquet writing |
| `build --limit 1000` | Same complete original-data pipeline |
| `collect --limit 1000` | Reviewed, explicitly permitted local text files from sources.yaml |
| `validate` | Bounded read-back, SHA-256, schema, evidence and lineage checks |
| `resume` | Recover complete orphan shards and continue last safe boundary |
| `status` | Durable actual counts, family/split/category statistics |
| `storage-report` | Measured compression and clearly qualified 30M projection |
| `upload` | Opt-in backend, finite quota, streamed remote checksum and manifest verification |
| `benchmark` | Held-out policy-validator self-check; not an LLM quality benchmark |
| `dry-run --limit 1000` | Resource estimates, no dataset writes |

Pilot generation is bounded by **1,344 candidate slots**, 10,000 candidates per job and 10,000 retained local records.
Slots are a finite mix of policy variants and original executable tasks. The builder stops when exhausted;
it cannot produce 30M by repeatedly changing names or random seeds. Add independently meaningful families,
licensed sources and richer verifiers before increasing any cap.

## Storage defaults for a laptop with 50 GB free

- Project-generated data plus controlled `.venv`, test/build and report folders: at most 15 GiB.
- Preserve at least 25 GiB free disk (about 26.8 decimal GB).
- Temporary staging: below 5 GiB; compressed shard hard cap: 128 MiB.
- Process RAM ceiling: 1.5 GiB; available-system-RAM floor: 256 MiB.
- Maximum configured workers: 2; the v1 local pipeline uses one writer.
- Persistent metadata cap: 128 MiB; source files and records capped at 256 KiB each.
- All staging, pipeline caches, SQLite/WAL files are counted. No repository cloning or global dataset download.
- Checks reserve a conservative prospective write allowance. Low disk/RAM pauses preserve the committed boundary.

Free space for dependency installation is checked separately; use `--no-cache-dir` as shown.
Other programs can consume disk concurrently, so no filesystem polling guard can guarantee the whole drive
never fills. This project never deletes personal files or accepts an unrelated nonempty workspace.

## Actual verification

See `docs/VERIFICATION.md`, `test-results.txt` and `data/reports/run-report.json` for measured evidence.
Records carry explicit verification kinds. Trusted Python execution is limited to original arithmetic expressions;
repository code is never executed. Generated fixes are deterministic catalog fixes, not outputs from a trained LLM.

## Remote publishing

Uploads are OFF by default. An external SSD implementation and local mock backend are tested.
Optional Hugging Face / S3 adapters are supplied but no live service was tested or uploaded to.
See `docs/STORAGE.md`. V1 intentionally retains completed local shards after verified upload;
only verified temporary staging copies can be cleaned by the cleanup helper. Therefore uploading does not
remove the local pilot cap: unattended million-record operation is not enabled in this release.
Provider account quotas must be checked separately from the configured per-destination byte budget.

## Files

`src/fullstackops/`: actual CLI, guard, schema, generation, trusted execution, collection, validation,
compression, deduplication, checkpoint/recovery, manifests, reporting and storage adapters.
`tests/`: bounded success/failure tests. `data/shards/`: nested ZSTD Parquet sample.
`data/manifests/`: immutable shard checksums and recovery boundaries. `docs/`: methodology and limitations.

Code and original synthetic examples use MIT. Reviewed source files retain their original licenses and attribution;
this does not grant permission to redistribute any unreviewed public code.
