# Schema 1.0

The authoritative strict schema is `src/fullstackops/schema.py`; `schema.json` is its generated JSON Schema.

| Group | Fields |
| --- | --- |
| Identity | record_id, schema_version, content_hash, created_at, record_split |
| Task | task_category, task_subcategory, programming_language, framework, difficulty, instruction |
| Context | environment (string map), repository_context, input_files (path/content structs), observations, error_logs |
| Agent evidence | agent_actions (step number, tool name/arguments, observed output, exit code, action result, next action) |
| Answer | expected_behavior, generated_patch (replacement file structs), test_commands, test_results |
| Quality | verification_status, quality_state, quality_score |
| Source | source_type, source_license, source_reference, source_commit, provenance |

verification_status: static_validated, syntax_validated, runtime_verified, synthetic_unverified.
verification_kind: static_policy, syntax, trusted_python. No value means successful real cloud deployment.
quality_state: RAW, NORMALIZED, SYNTHETIC_UNVERIFIED, VALIDATION_FAILED, VALIDATED, REVIEWED.
The delivered pipeline persists accepted states; rejected candidates are counted, not stored as secret-bearing raw data.
`synthetic_unverified` is a conservative schema label also used for unparsed reviewed local text, whose source_type
remains reviewed_local. Training subsets must use both source_type and verification_status.

`generated_patch` is a minimal whole-file replacement, not a unified Git diff. Tool arguments are JSON strings;
all actual observed results remain explicit nested evidence fields. The three generated steps describe trusted
validation calls plus their next action; they are not traces of an autonomous deployed agent.

record_split is deterministic by template/repository family and seed: approximately 75% train, 10% validation,
10% test and 5% heldout at family level. Small catalogs need not match these percentages exactly. Changing a
seed in an existing workspace can trigger the cross-split leakage guard. Use a new dataset version/workspace.
