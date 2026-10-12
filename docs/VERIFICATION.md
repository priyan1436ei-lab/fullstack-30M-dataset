# Verification evidence — 12 October 2026

Outcome: working v0.1 local builder and a real 1,000-record pilot. The 30M corpus is not complete.

| Check | Result |
| --- | --- |
| Automated pytest suite | 24 passed; see test-results.txt |
| Pilot record count | 1,000 |
| Strict schema and nested Parquet read-back | 1,000 validated |
| Static policy baseline/fault/fix evidence | 875 records |
| Actual trusted Python baseline/fault/fix execution | 125 records |
| Original independent families | 63 (56 policy, 7 arithmetic) |
| Cross-split lineage leakage | 0 |
| Canonical duplicate rejection | Persistent SQLite unique index and resume tests pass |
| Repeated resume | Remains at 1,000 records |
| Compressed Parquet | 694,037 bytes, 16 SHA-256 manifests |
| Observed process peak RSS | 158,035,968 bytes |
| Storage safety | Free-space, workspace, staging and RAM-pressure test cases pause safely |
| Interruption and recovery | Committed-boundary resume and complete-orphan-shard recovery tested |
| Upload corruption/quota | Filesystem mock tests preserve valid local copies |
| Real remote upload | Not configured / not performed |
| Native Windows execution | Not performed; portable code and PowerShell commands supplied |
| Real service/container/cloud verification | Not performed |

`final-validation-output.json`, `final-resume-output.json`, `environment-report.json` and
`data/reports/run-report.json` contain the measured outputs. Numeric storage snapshots refer to this
execution environment, not Priyan's laptop. Doctor recalculates them on the laptop before work.

No credentials or external source files were collected. Tests use temporary directories and small mock
objects. The original-execution test rejects arbitrary replacement code before any execution.
The implementation never uses shell commands from dataset records.

Remaining engineering work: independent rich application tasks, full platform validators, hardened workers,
semantic near-dedup, metadata archival, verified remote-only recovery and transactional local shard removal.
The local caps intentionally prevent unsupported unattended scaling.
