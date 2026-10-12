import json
from .storage_guard import StorageGuard
from .manifests import atomic_json
TARGETS={'fullstack':6000000,'docker':4000000,'cicd':4000000,'cloud':4000000,'errors':4000000,'infra':3000000,'security':3000000}
def report(s,state,write=False):
    db=state.db;shards=list(state.shards());counts=dict(db.execute('SELECT name,value FROM counters'))
    accepted=db.execute('SELECT COUNT(*) FROM records').fetchone()[0]
    statuses=dict(db.execute('SELECT status,COUNT(*) FROM records GROUP BY status'))
    raw=sum(x['manifest']['raw_bytes'] for x in shards);compressed=sum(x['bytes'] for x in shards)
    categories=dict(db.execute('SELECT category,COUNT(*) FROM records GROUP BY category'))
    families=db.execute('SELECT COUNT(DISTINCT family) FROM records').fetchone()[0]
    duplicates=counts.get('duplicates',0)
    candidates=accepted+sum(counts.get(k,0) for k in ('duplicates','license_rejections','security_rejections','validation_failures'))
    r=dict(project='FullStackOps-30M',long_term_target=30000000,actual_records=accepted,
       candidate_records=candidates,accepted_records=accepted,rejected_duplicates=duplicates,
       duplicate_percentage=100*duplicates/max(1,candidates),rejected_license=counts.get('license_rejections',0),
       license_rejection_percentage=100*counts.get('license_rejections',0)/max(1,candidates),
       rejected_security=counts.get('security_rejections',0),validation_failures=counts.get('validation_failures',0),
       policy_validated_records=statuses.get('static_validated',0),syntax_validated_records=statuses.get('syntax_validated',0),
       runtime_verified_records=statuses.get('runtime_verified',0),executed_runtime_trajectories=statuses.get('runtime_verified',0),unverified_records=statuses.get('synthetic_unverified',0),
       original_synthetic_records=db.execute("SELECT COUNT(*) FROM records WHERE status IN ('static_validated','runtime_verified')").fetchone()[0],
       real_source_records=accepted-statuses.get('static_validated',0)-statuses.get('runtime_verified',0),unique_task_families=families,
       unique_source_repositories=1 if accepted==statuses.get('static_validated',0)+statuses.get('runtime_verified',0) and accepted else None,
       records_by_category=categories,records_by_split=dict(db.execute('SELECT split,COUNT(*) FROM records GROUP BY split')),
       category_targets=TARGETS,raw_bytes=raw,compressed_bytes=compressed,compression_ratio=raw/max(1,compressed),
       average_compressed_bytes_per_record=compressed/max(1,accepted),
       measured_30m_projection_bytes=round(compressed/max(1,accepted)*30000000),
       projection_caveat='Pilot policy records only; richer code/log/runtime tasks may be much larger. This is not a capacity promise.',
       completed_shards=len(shards),uploaded_shards=sum(x['uploaded'] for x in shards),
       pending_uploads=sum(not x['uploaded'] for x in shards),uploaded_bytes=sum(x['bytes'] for x in shards if x['uploaded']),
       peak_process_rss_bytes=counts.get('peak_rss',0),pipeline_failures=counts.get('pipeline_failures',0),
       current_job=state.job(),storage=StorageGuard(s).generate_storage_report())
    if write:
        atomic_json(s.workspace/'reports'/'run-report.json',r,StorageGuard(s))
        text=f"FullStackOps-30M pilot report\n\nActual records: {accepted}\nStatic policy validated: {r['policy_validated_records']}\nRuntime verified: {r['runtime_verified_records']}\nFamilies: {families}\nCompressed bytes: {compressed}\n30M measured extrapolation: {r['measured_30m_projection_bytes']} bytes\n\n{r['projection_caveat']}\n"
        StorageGuard(s).validate_write_budget(len(text.encode())+4096)
        (s.workspace/'reports'/'run-report.txt').write_text(text)
    return r
