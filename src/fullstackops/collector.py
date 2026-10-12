"""Reviewed bounded local ingestion. Never executes or clones source material."""
from pathlib import Path
import ast,hashlib,yaml
from .schema import Record,now
from .validator import LICENSES,security_scan
from .normalizer import content_hash,split_for
class SourceRejected(ValueError): pass

def discover(config):
    p=Path(config)
    if p.stat().st_size>1024*1024: raise SourceRejected('source manifest too large; partition it into bounded jobs')
    entries=yaml.safe_load(p.read_text()).get('sources',[]) or []
    if len(entries)>10000:raise SourceRejected('source manifest exceeds 10000-entry cap')
    return entries

def collect_one(source,seed,max_bytes=262144):
    required=('id','path','license','reviewed','redistribution_allowed','source_url','repository','commit','attribution')
    if any(k not in source for k in required): raise SourceRejected("incomplete provenance")
    if source['reviewed'] is not True or source['redistribution_allowed'] is not True or source['license'] not in LICENSES:
        raise SourceRejected("license/permission review required")
    p=Path(source['path'])
    if p.is_symlink() or not p.is_file() or p.stat().st_size>max_bytes: raise SourceRejected("unsafe or oversized source")
    content=p.read_bytes()[:max_bytes+1].decode('utf-8')
    if len(content.encode())>max_bytes or security_scan(content): raise SourceRejected("security or size rejection")
    ext=p.suffix
    if ext not in ('.py','.yaml','.yml','.json','.toml','.md','.txt'): raise SourceRejected("unsupported text format")
    import json,tomllib
    syntax="unverified"
    if ext=='.py': ast.parse(content); syntax="syntax_validated"
    elif ext in ('.yaml','.yml'): yaml.safe_load(content);syntax="syntax_validated"
    elif ext=='.json': json.loads(content);syntax="syntax_validated"
    elif ext=='.toml': tomllib.loads(content);syntax="syntax_validated"
    time=now();lineage=str(source['repository'])
    results=[] if syntax=='unverified' else [dict(phase="syntax",command=f"internal.parse:{ext}",exit_code=0,output="Parser accepted source; runtime untested",verification_kind="syntax")]
    r=Record(record_id=hashlib.sha256(f"{source['id']}:{source['commit']}:{p.name}:{content}".encode()).hexdigest(),
        task_category="fullstack",task_subcategory="reviewed-source",programming_language=ext[1:],framework="unspecified",difficulty="medium",
        instruction="Study this reviewed source example; no runtime verification is claimed.",environment={"execution":"none"},repository_context=str(source['repository']),
        input_files=[dict(path=p.name,content=content)],observations=[],error_logs=[],agent_actions=[],expected_behavior="Source reference only; no expected runtime outcome.",
        generated_patch=[],test_commands=[t['command'] for t in results],test_results=results,
        verification_status="synthetic_unverified" if syntax=='unverified' else syntax,quality_state="SYNTHETIC_UNVERIFIED" if syntax=='unverified' else "VALIDATED",
        quality_score=0.3,source_type="reviewed_local",source_license=source['license'],source_reference=source['source_url'],source_commit=source['commit'],
        provenance=dict(source_url=source['source_url'],repository_identifier=lineage,commit_revision=source['commit'],file_path=p.name,
        attribution=source['attribution'],collected_at=time,redistribution_allowed=True,provenance_category="reviewed_local",template_id="reviewed-source",
        mutation_id="none",source_family=lineage,lineage=lineage),created_at=time,content_hash="",record_split=split_for(lineage,seed))
    r.content_hash=content_hash(r);return r
