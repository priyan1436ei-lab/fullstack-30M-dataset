import json,uuid,hashlib
from pathlib import Path
import psutil
import pyarrow.parquet as pq
from .storage_guard import StorageGuard,PipelinePaused,process_rss
from .checkpoint import State
from .deduplicator import Deduplicator
from .generator import generate_one,MAX_SYNTHETIC
from .collector import discover,collect_one,SourceRejected
from .validator import validate_record
from .compressor import Compressor
from .metrics import report
from .manifests import sha256_file,atomic_json

def initialize(s):
    guard=StorageGuard(s);guard.validate_write_budget(2*1024**2)
    marker=s.workspace/'.fullstackops-workspace'
    if s.workspace.exists() and any(s.workspace.iterdir()) and not marker.exists():
        raise ValueError('workspace is nonempty and not owned by FullStackOps; choose a new dedicated folder')
    s.workspace.mkdir(parents=True,exist_ok=True)
    if marker.exists() and marker.read_text()!='fullstackops-v1': raise ValueError('workspace marker invalid')
    marker.write_text('fullstackops-v1')
    for name in ('staging','shards','manifests','reports','cache','tmp'):
        (s.workspace/name).mkdir(parents=True,exist_ok=True)
    state=State(s.workspace);state.close()

def source_fingerprint(s,mode,sources=None):
    if mode=='generate':
        value=f'catalog-v1-trusted-exec:{s.seed}:{MAX_SYNTHETIC}'
        for name in ('generator.py','execution.py','validator.py','schema.py'):
            value+=sha256_file(Path(__file__).parent/name)
    else:
        # Prevent source edits/reordering from silently changing a resumed job.
        value=json.dumps(sources,sort_keys=True)
        for source in sources:
            p=Path(source.get('path',''))
            if p.is_file() and p.stat().st_size<=s.max_record_bytes: value+=sha256_file(p)
    return hashlib.sha256(value.encode()).hexdigest()

def recover(s,state,guard):
    # A complete Parquet file is the write-ahead record; SQLite commit may have been interrupted.
    known={x['name']:x for x in state.shards()}
    for path in sorted((s.workspace/'shards').glob('*.parquet')):
        guard.validate_write_budget()
        if path.name in known:
            if sha256_file(path)!=known[path.name]['checksum']: raise ValueError('committed shard checksum mismatch')
            continue
        guard.validate_write_budget(s.max_record_bytes*s.row_group_records*4)
        pf=pq.ParquetFile(path)
        if pf.metadata.num_rows>s.row_group_records or path.stat().st_size>s.shard_bytes: raise ValueError('oversized recovery shard')
        metadata=json.loads(pf.schema_arrow.metadata[b'fullstackops_job'])
        if state.job() is None or metadata['id']!=state.job()['id']: raise ValueError('orphan belongs to unknown job')
        rows=[validate_record(x) for x in pf.read().to_pylist()]
        m=dict(name=path.name,sha256=sha256_file(path),records=len(rows),raw_bytes=sum(len(r.model_dump_json().encode()) for r in rows),
            compressed_bytes=path.stat().st_size,schema_version='1.0',job=metadata,verification_subset=rows[0].verification_status,
            splits=sorted({r.record_split for r in rows}))
        atomic_json(s.workspace/'manifests'/f'{path.name}.json',m,guard)
        with state.db:
            state.register(m,rows)
            state.progress(metadata['id'],metadata['next_offset'])
    # Incomplete files are owned staging artifacts only. Never remove completed shards.
    for partial in (s.workspace/'staging').glob('*.partial'):
        if partial.is_file() and not partial.is_symlink(): partial.unlink()

def _run(s,limit=1000,mode='generate',resume=False,stop_after_shards=None):
    if not 1<=limit<=s.max_job_candidates: raise ValueError('limit exceeds bounded job cap')
    initialize(s);guard=StorageGuard(s);state=State(s.workspace)
    try:
        recover(s,state,guard)
        sources=discover(s.sources_file) if mode=='collect' else None
        job=state.job()
        if resume:
            if not job: raise ValueError('no previous job')
            mode=job['mode'];limit=job['target'];sources=discover(s.sources_file) if mode=='collect' else None
        fingerprint=source_fingerprint(s,mode,sources)
        if resume:
            if fingerprint!=job['source_fingerprint']: raise ValueError('source catalog changed; resume refused')
            if job['status']=='completed': return report(s,state,True)
            start=job['source_offset']
        else:
            if job and job['status']!='completed': raise ValueError('unfinished job exists; use resume')
            start=0 if not job or mode!=job['mode'] else job['source_offset']
            if mode=='generate' and start>=MAX_SYNTHETIC: raise ValueError('finite pilot catalog exhausted; add independent scenarios')
            if mode=='generate': limit=min(limit,MAX_SYNTHETIC-start)
            else: limit=min(limit,max(0,len(sources)-start))
            state.start(uuid.uuid4().hex,mode,start+limit,fingerprint)
            job=state.job();job['source_offset']=start
            state.progress(job['id'],start);state.db.commit()
        offset=start;batch=[];batch_hashes=set();count=0
        dedup=Deduplicator(state);compressor=Compressor(s,guard)
        def flush():
            nonlocal batch,batch_hashes,count
            if not batch:
                state.progress(job['id'],offset);state.db.commit();return
            guard.validate_write_budget(s.max_record_bytes*len(batch)*4+2*1024**2)
            name=f"{job['id']}-{offset:08d}-{batch[0].verification_status}.parquet"
            m=compressor.write(batch,name,dict(id=job['id'],next_offset=offset,mode=mode,source_fingerprint=fingerprint))
            with state.db:
                state.register(m,batch);state.progress(job['id'],offset)
            batch=[];batch_hashes=set();count+=1
            if s.allow_upload and s.backend!='none':
                from .uploader import upload_pending
                upload_pending(s,state,guard)
            if stop_after_shards is not None and count>=stop_after_shards: raise PipelinePaused('requested test interruption')
        try:
            while offset<job['target']:
                guard.validate_write_budget(s.max_record_bytes*8)
                if sum(p.stat().st_size for p in s.workspace.glob('state.sqlite*'))+s.max_record_bytes>=s.metadata_bytes:
                    raise PipelinePaused('metadata index budget reached; v1 requires manual archiving')
                total=state.db.execute('SELECT COUNT(*) FROM records').fetchone()[0]
                if total+len(batch)>=s.max_local_records: raise PipelinePaused('local pilot record cap reached; review scaling plan')
                current=offset
                try:
                    r=generate_one(current,s.seed) if mode=='generate' else collect_one(sources[current],s.seed,s.max_record_bytes)
                    r=validate_record(r)
                    if len(r.model_dump_json().encode())>s.max_record_bytes: raise ValueError('record byte cap exceeded')
                    dedup.check_split(r)
                    duplicate=dedup.is_duplicate(r) or r.content_hash in batch_hashes
                    if not duplicate and batch and batch[0].verification_status!=r.verification_status: flush()
                    state.count('candidates')
                    if duplicate: state.count('duplicates')
                    else:
                        batch.append(r);batch_hashes.add(r.content_hash)
                except SourceRejected as exc:
                    state.count('candidates');state.count('security_rejections' if 'security' in str(exc) else 'license_rejections')
                except (ValueError,SyntaxError) as exc:
                    state.count('candidates');state.count('validation_failures')
                offset+=1
                rss=process_rss()
                state.db.execute('INSERT INTO counters VALUES (?,?) ON CONFLICT(name) DO UPDATE SET value=MAX(value,excluded.value)',('peak_rss',rss))
                if len(batch)>=s.row_group_records: flush()
            flush();state.progress(job['id'],offset,'completed');state.db.commit()
        except (PipelinePaused,KeyboardInterrupt,MemoryError) as exc:
            # Discard uncommitted in-memory rows; retry from the last committed boundary.
            state.db.rollback()
            committed=state.job()['source_offset']
            state.progress(job['id'],committed,'paused',str(exc) or type(exc).__name__);state.db.commit()
        except Exception as exc:
            state.db.rollback();committed=state.job()['source_offset'];state.count('pipeline_failures')
            state.progress(job['id'],committed,'paused',str(exc));state.db.commit();raise
        return report(s,state,True)
    finally: state.close()

def validate_shards(s):
    state=State(s.workspace);n=0
    try:
        for shard in state.shards():
            StorageGuard(s).validate_write_budget()
            p=s.workspace/'shards'/shard['name']
            if sha256_file(p)!=shard['checksum']: raise ValueError('checksum mismatch')
            pf=pq.ParquetFile(p)
            for batch in pf.iter_batches(batch_size=s.row_group_records):
                for row in batch.to_pylist(): validate_record(row);n+=1
        contamination=state.db.execute('SELECT family FROM records GROUP BY family HAVING COUNT(DISTINCT split)>1').fetchall()
        if contamination: raise ValueError('split leakage')
        return {'readback_validated_records':n,'cross_split_lineage_leaks':0}
    finally: state.close()


def run(s,limit=1000,mode='generate',resume=False,stop_after_shards=None):
    initialize(s)
    from .locking import writer_lock
    with writer_lock(s.workspace):
        return _run(s,limit,mode,resume,stop_after_shards)
