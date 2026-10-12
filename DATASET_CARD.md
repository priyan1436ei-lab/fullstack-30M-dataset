---
language:
- en
license: mit
task_categories:
- text-generation
---
# FullStackOps-30M — v0.1 pilot

30,000,000 is a long-term target. This release has **1,000 actual records**.

| Metric | Delivered result |
| --- | ---: |
| Original synthetic records | 1,000 |
| Static configuration-policy checks | 875 |
| Runtime-verified original Python calculations | 125 |
| Real external-source records / repositories | 0 / 0 |
| Source repository families | 1 original project |
| Distinct task families | 63 |
| Executed calculation trajectories | 125 |
| Unverified records | 0 |
| Real Docker builds / cloud deployments | 0 / 0 |
| Parquet shards | 16 |
| Compressed Parquet bytes | 694,037 |

Records include deterministic catalog fixes, configuration files, real test results, provenance,
permissions, family-level splits, canonical hashes and tool observations. Policy checks verify one field
against an explicitly declared requirement. Python checks execute original finite arithmetic expressions.
These are small instructional tasks, not autonomous-agent traces or production deployment success evidence.

## Intended use

Inspect dataset engineering, provenance, recovery and bounded resource-management tasks. Use the pilot
for experimentation and pipeline validation; it is insufficient to train a capable full-stack coding model.
All Python arithmetic is trusted original code. Reviewed repository execution is not enabled.

## Distribution

Category counts: {"cicd": 146, "cloud": 146, "docker": 146, "errors": 141, "fullstack": 145, "infra": 138, "security": 138}.
Split counts: {"heldout": 16, "test": 110, "train": 748, "validation": 126}.
Splits are assigned by template/source family, not randomly by record. Parameters of each family are
correlated. 1,000 rows must not be advertised as 1,000 independent problems.
Targets for the future corpus remain 6M full-stack, 4M Docker, 4M CI/CD, 4M cloud, 4M errors,
3M infrastructure and 3M security/recovery. These quotas have not been collected.

## Storage

Measured average compressed bytes per record: 694.04.
Measured pilot-only extrapolation to 30M: 20,821,110,000 bytes
(20.82 decimal GB). Rich code files, repository context and
multi-step deployment logs can be much larger. This projection is not a storage guarantee.

## License / limitations

Original code and original examples: MIT. No external sources were ingested. Future reviewed sources
retain their individual licenses and required notices. Automated secret/PII detection is heuristic.
Native Dockerfile/Compose, Kubernetes, Terraform or cloud API validation is not demonstrated by a policy check.
There are no LLM-generated solutions, calibrated quality scores, live remote publication, hardened untrusted
repository workers, external near-dedup service or automatic metadata archival in this pilot.
Local output is capped, and completed local copies are retained after upload. V1 safely stops before scale.
Windows setup commands are included; validation ran on Linux with Python 3.12.
