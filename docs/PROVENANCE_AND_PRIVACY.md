# Provenance, permissions and privacy

The original v1 catalog and code are authored for this project and released under MIT. Every record retains
origin URL, repository/family, commit/catalog revision, file path, license, attribution, collection time,
redistribution permission, template and mutation IDs. Original examples are marked original_synthetic.
No external repositories, documents or production logs were collected for the delivered pilot.

Source ingestion requires a reviewer to affirm the exact license and redistribution permission in sources.yaml.
The allowlist is MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause and CC0-1.0. Preserve license notices, copyright
and attribution for each reviewed source when publishing; a source manifest alone is not a legal audit.
Do not use private code, unknown-license content, production secrets or sensitive logs.

The automated filter detects common tokens, private keys, password/API-key assignments, email addresses and
Indian phone-like numbers. It can have false positives and false negatives; it does not establish comprehensive
PII removal or certification of a corpus. Review final data before publication. The pilot contains no source
credentials. Remote credentials come only from environment variables and are never copied into training records.

The builder never runs commands from records or untrusted sources. Only original catalog expressions execute.
There are no cloud deployments, payments or real infrastructure mutations. Hardened repository execution,
Docker builds, networked testing and production-grade sandbox resource controls are not implemented in v1.
Deletion is limited to owned incomplete staging files and explicitly verified staging cleanup. Completed dataset
shards and unrelated folders are retained. A dedicated workspace ownership marker and single-writer lock protect
against accidental reuse and concurrent local builders.
