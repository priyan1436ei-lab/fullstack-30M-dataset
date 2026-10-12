import json,shutil
from pathlib import Path
import pytest
import pyarrow.parquet as pq
from fullstackops.settings import Settings
from fullstackops.storage_guard import StorageGuard,PipelinePaused
from fullstackops.generator import generate_one,MAX_SYNTHETIC
from fullstackops.validator import validate_record,security_scan
from fullstackops.pipeline import run,validate_shards,recover
from fullstackops.checkpoint import State
from fullstackops.uploader import MockBackend,upload_pending,backend_for
from fullstackops.compressor import Compressor
from fullstackops.collector import collect_one,SourceRejected
from fullstackops.normalizer import content_hash

@pytest.fixture
def settings(tmp_path):
    return Settings(workspace=tmp_path/'data',min_free_bytes=1,max_workspace_bytes=128*1024**2,
                    max_temp_bytes=16*1024**2,row_group_records=8,metadata_bytes=16*1024**2)

def test_config_defaults_are_laptop_safe():
    s=Settings();assert s.max_workspace_bytes==15*1024**3 and s.min_free_bytes==25*1024**3
    assert s.max_workers<=2 and not s.allow_upload

def test_disk_reserve_pause(settings,monkeypatch):
    g=StorageGuard(settings);monkeypatch.setattr(g,'check_free_space',lambda:100)
    settings.min_free_bytes=90
    with pytest.raises(PipelinePaused):g.validate_write_budget(11)

def test_workspace_and_temp_budget(settings,monkeypatch):
    g=StorageGuard(settings);monkeypatch.setattr(g,'check_workspace_size',lambda:settings.max_workspace_bytes-10)
    with pytest.raises(PipelinePaused):g.validate_write_budget(10)
    monkeypatch.setattr(g,'check_workspace_size',lambda:0)
    monkeypatch.setattr(g,'temp_size',lambda:settings.max_temp_bytes)
    with pytest.raises(PipelinePaused):g.validate_write_budget()

def test_memory_pause(settings,monkeypatch):
    import fullstackops.storage_guard as mod
    class Memory: available=0
    monkeypatch.setattr(mod.psutil,'virtual_memory',lambda:Memory())
    with pytest.raises(PipelinePaused):StorageGuard(settings).validate_write_budget()

def test_schema_and_fabrication_rejected():
    r=generate_one(0);validate_record(r)
    r.test_results[2].output='invented successful deployment'
    with pytest.raises(ValueError):validate_record(r)

def test_split_lineage_and_finite_catalog():
    a=generate_one(0);b=generate_one(56)
    assert a.record_split==b.record_split and a.content_hash!=b.content_hash
    with pytest.raises(ValueError):generate_one(MAX_SYNTHETIC)

def test_secret_and_pii_scanning():
    for text in ('ghp_'+'a'*30,'-----BEGIN PRIVATE KEY-----','AKIA'+'A'*16,'person@example.org','9876543210','password=verysecretvalue'):
        assert security_scan(text)

def test_unknown_license_rejected(tmp_path):
    p=tmp_path/'x.py';p.write_text('print(1)')
    with pytest.raises(SourceRejected):collect_one(dict(id='x',path=str(p),license='unknown',reviewed=True,redistribution_allowed=True,
            source_url='local://x',repository='x',commit='v1',attribution='Author'),42)

def test_reviewed_source_parser_only(tmp_path):
    p=tmp_path/'x.py';p.write_text('print(1)')
    r=collect_one(dict(id='x',path=str(p),license='MIT',reviewed=True,redistribution_allowed=True,
            source_url='local://x',repository='x',commit='v1',attribution='Author'),42)
    assert r.verification_status=='syntax_validated';validate_record(r)

def test_interruption_and_resume(settings):
    first=run(settings,40,stop_after_shards=1)
    assert first['actual_records']==8 and first['current_job']['status']=='paused'
    result=run(settings,resume=True)
    assert result['actual_records']==40 and result['current_job']['status']=='completed'
    assert validate_shards(settings)['readback_validated_records']==40
    assert run(settings,resume=True)['actual_records']==40
    state=State(settings.workspace)
    assert state.db.execute('SELECT COUNT(DISTINCT hash) FROM records').fetchone()[0]==40
    state.close()

def test_1000_pilot(settings):
    settings.row_group_records=64
    r=run(settings,1000)
    assert r['actual_records']==1000 and r['policy_validated_records']==875
    assert r['runtime_verified_records']==125 and r['validation_failures']==0
    assert sum(r['records_by_split'].values())==1000
    assert validate_shards(settings)['cross_split_lineage_leaks']==0

def test_safe_pause_preserves_commit(settings,monkeypatch):
    run(settings,32,stop_after_shards=1)
    original=StorageGuard.validate_write_budget
    calls=0
    def fail_later(self,*args,**kwargs):
        nonlocal calls
        calls+=1
        if calls==4: raise PipelinePaused('injected disk pressure')
        return original(self,*args,**kwargs)
    monkeypatch.setattr(StorageGuard,'validate_write_budget',fail_later)
    result=run(settings,resume=True)
    assert result['current_job']['status']=='paused' and result['actual_records']>=8
    monkeypatch.setattr(StorageGuard,'validate_write_budget',original)
    assert run(settings,resume=True)['actual_records']==32

def test_orphan_shard_recovery(settings):
    run(settings,24,stop_after_shards=1)
    state=State(settings.workspace);job=state.job()
    records=[generate_one(i) for i in range(8,16)]
    Compressor(settings,StorageGuard(settings)).write(records,job['id']+'-orphan.parquet',
        dict(id=job['id'],next_offset=16,mode='generate',source_fingerprint=job['source_fingerprint']))
    state.close()
    assert run(settings,resume=True)['actual_records']==24

def test_corrupt_shard_rejected(settings):
    run(settings,8)
    p=next((settings.workspace/'shards').glob('*.parquet'));p.write_bytes(b'corrupt')
    with pytest.raises(ValueError):validate_shards(settings)

def test_upload_disabled(settings):
    with pytest.raises(RuntimeError):backend_for(settings)

def test_mock_upload_and_integrity(settings,tmp_path):
    run(settings,16)
    state=State(settings.workspace);mock=MockBackend(tmp_path/'remote',10*1024**2)
    assert upload_pending(settings,state,StorageGuard(settings),mock)==2
    assert upload_pending(settings,state,StorageGuard(settings),mock)==0
    assert len(list(mock.list_shards()))==2
    assert all(x['uploaded'] for x in state.shards())
    state.close()

def test_corrupt_upload_preserves_valid_copy(settings,tmp_path):
    run(settings,8);state=State(settings.workspace)
    class Corrupt(MockBackend):
        def upload_shard(self,path,key):
            super().upload_shard(path,key);self.path(key).write_bytes(b'bad')
    mock=Corrupt(tmp_path/'remote',10*1024**2)
    with pytest.raises(Exception):upload_pending(settings,state,StorageGuard(settings),mock)
    assert not next(state.shards())['uploaded']
    assert next((settings.workspace/'shards').glob('*.parquet')).exists()
    state.close()

def test_destination_quota(settings,tmp_path):
    run(settings,8);state=State(settings.workspace);mock=MockBackend(tmp_path/'remote',1)
    with pytest.raises(RuntimeError):upload_pending(settings,state,StorageGuard(settings),mock)
    assert not next(state.shards())['uploaded'];state.close()

def test_safe_cleanup_only_staging(settings,tmp_path):
    run(settings,8);mock=MockBackend(tmp_path/'remote',10*1024**2)
    p=next((settings.workspace/'shards').glob('*.parquet'))
    with pytest.raises(ValueError):StorageGuard(settings).cleanup_verified_temporary_files(p,'x',mock)
    assert p.exists()

def test_bounded_shard(settings):
    settings.shard_bytes=65536
    result=run(settings,8)
    assert all(p.stat().st_size<=65536 for p in (settings.workspace/'shards').glob('*.parquet'))

def test_dry_run_has_no_writes(settings,tmp_path,capsys):
    from fullstackops.cli import main
    import yaml
    config=tmp_path/'settings.yaml';config.write_text(yaml.safe_dump(settings.model_dump(mode='json')))
    assert main(['--config',str(config),'dry-run','--limit','10'])==0
    assert not settings.workspace.exists()

def test_trusted_python_evidence_and_arbitrary_code_rejected():
    r=generate_one(875);assert r.verification_status=='runtime_verified';validate_record(r)
    r.generated_patch[0].content='result = __import__("os").system("echo unsafe")\n'
    r.content_hash=content_hash(r)
    with pytest.raises(ValueError):validate_record(r)

def test_unrelated_workspace_refused(settings):
    settings.workspace.mkdir();p=settings.workspace/'personal.txt';p.write_text('keep')
    with pytest.raises(ValueError):run(settings,1)
    assert p.read_text()=='keep'

def test_single_writer_lock(settings):
    from fullstackops.pipeline import initialize
    from fullstackops.locking import writer_lock
    initialize(settings)
    with writer_lock(settings.workspace):
        with pytest.raises(RuntimeError):
            with writer_lock(settings.workspace): pass
