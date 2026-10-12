# Storage and scaling

Default limits use binary units (GiB/MiB). With 50 decimal GB free, the guard preserves 26.84 GB;
the 15 GiB workspace maximum is 16.11 decimal GB. The free-reserve constraint takes precedence.
The guard counts all files, including SQLite WAL/SHM and owned hidden caches, under the workspace,
plus controlled `.venv`, `.pytest_cache`, build, dist, logs and reports directories beside it.
It checks free disk and RAM before candidate processing, batch serialization, file writes and uploads.
It refuses symlinked workspaces and requires an ownership marker before touching an existing nonempty folder.

Parquet is written one bounded row group per completed shard. The 128 MiB setting is a ceiling, not padding:
pilot shards are much smaller. Serialization is buffered conservatively, schema/read-back validated, SHA-256
checksummed and renamed atomically. Footer and compression overhead count toward the hard cap.
An oversized row group causes a pause; reduce row_group_records to proceed. SQLite metadata stops at 128 MiB.
The pipeline uses one writer; its lock prevents simultaneous builders modifying the same workspace.

## External SSD example

Copy the settings file, retaining the laptop-safe thresholds:

```yaml
backend: external
destination: "E:/FullStackOpsArchive"
remote_quota_bytes: 10737418240
allow_upload: true
```

`destination` must be outside the data workspace. The configured quota is finite; existing objects and free
space are inspected before copying. Run `python -m fullstackops --config config/external.yaml upload`.
Only run with an existing SSD/volume and a destination you authorize. A typo can create a folder on the wrong
volume, so verify the destination with your OS first. No drive is assumed to be attached.

Every upload follows: local checksum -> copy/upload -> streamed remote checksum -> remote per-shard manifest
-> read-back of manifest -> SQLite uploaded checkpoint. Retries are bounded to three attempts.
The final local shards are retained in v1. The provided staging cleanup helper deletes only an owned staging
copy after re-verifying the remote checksum. It refuses completed final shards and unrelated files.

## Optional adapters

S3: install `.[s3]`; configure backend `s3`, destination `s3://bucket/prefix`, quota and `allow_upload: true`.
Use environment credentials and optional s3_endpoint. Credentials never enter records. Transfer concurrency is 1.
Hugging Face: install `.[hf]`; configure backend `hf`, destination `owner/dataset`, quota and authorization.
Set HF_TOKEN in your shell. Create/review the repository yourself first. Integrity checking streams downloads;
no complete remote corpus is fetched. These adapters have not been live-tested in this delivery.
Byte-budget checks measure current listed objects; provider billing, history storage and account quotas require
separate verification. Shared destinations may race with external writers; use a dedicated prefix/repository.

## Honest scaling roadmap

1. Reproduce and inspect the 1,000-record pilot; validate task relevance before training.
2. Add independent full-stack, Docker, CI, infrastructure and recovery task families with stronger evidence.
3. Collect small reviewed source batches; retain per-file license and attribution.
4. Design hardened isolated workers for repository execution, with CPU, RAM, wall-time, disk, process and
   network limits. Ordinary Docker alone is not treated as an untrusted-code sandbox.
5. For 100K or 1M+, implement archived persistent dedup indexes and recoverable remote-only shard validation,
   plus transactional cleanup after remote verification. V1 stops before its local metadata/data caps.
6. Measure richer shards. Reserve provider storage, bandwidth and budget. Expand quality-reviewed quotas gradually.

30M is a goal, not a delivered corpus or an enabled unattended command. Pilot compression cannot predict
large repository files, multi-step logs, binaries or deployment traces reliably.
