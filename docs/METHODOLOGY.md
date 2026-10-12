# Collection, generation and quality methodology

V1 generates its own original scenarios offline. Policy tasks start with valid YAML plus a known configuration
requirement; one field is changed; actual baseline, failing and fixed checks are run against that requirement.
These are **service-policy files**, not necessarily native Docker Compose, CI, cloud or Kubernetes manifests.
Framework labels describe scenario context and do not establish platform conformance.

Python tasks use seven original finite calculation families: replica ceiling, bounded retry, memory division,
rolling batch size, disk-boundary permission, timeout equality and readiness equality. The trusted runner selects
only fixed catalog expressions and internally generated bounded numerical inputs. It compiles/evaluates them
without imports, shell, file I/O, loops, network or a general builtin namespace. An independent oracle checks the
actual output. The fault is confirmed to fail; the same input must pass after the minimal catalog correction.
Records explicitly distinguish these small runtime checks from configuration validation and real deployment.

Permitted sources: user-authored or reviewed local files with full provenance, explicit redistribution permission
and allowlisted license. `config/sources.yaml` is empty by default. URLs record origin only, never permission.
There is no automatic public-site scraping, GitHub cloning or access-control bypass. Unknown licenses are rejected.
The local collector streams one bounded file at a time, with a manifest of at most 10K entries / 1 MiB.
Supported text suffixes: Python, YAML, JSON, TOML, Markdown and plain text. Parsers verify syntax only;
Markdown/text are retained in a separately marked unverified subset. Nothing collected is executed.

The strict Pydantic schema rejects unexpected fields and dishonest baseline/fault/fix evidence. The pipeline checks
license, permission, source lineage, path safety, secret/PII patterns, canonical content hash and trajectory evidence.
Parquet output is read back before atomic completion and again by `validate`. It is ZSTD-compressed with nested
file/provenance/action/test structures. Output groups verification subsets into separate shards.

Persistent SQLite unique indexes enforce canonical content, record identity and source identity across batches.
All parameters of a template or repository family share one seed-derived split. Split changes that would mix an
existing source family are rejected. Exact and canonical dedup are hard gates; template ID and lineage are
retained for audits. A bounded lexical near-duplicate similarity utility is supplied for diagnostics, not a
semantic novelty guarantee. Parameter variants remain correlated, and counts always disclose independent families.

Reports count actual committed records, validation states and categories. The 30M projection uses observed total
compressed bytes / record count, including the unusually small shards in this pilot. Quality scores are transparent
fixed heuristics (0.65 policy, 0.80 trusted arithmetic, 0.30 reviewed sources), not calibrated probabilities.

Publication checklist: validate all checksums; inspect samples and license/PII findings; run held-out self-checks;
retain attribution and limitations; review provider quotas; configure explicit upload authorization; publish a
versioned card and manifests. Upload is disabled until configuration is supplied.
