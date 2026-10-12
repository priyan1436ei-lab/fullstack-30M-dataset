"""Uploads are opt-in and quota bounded. Remote integrity is checked by reading bytes."""
import abc,hashlib,json,os,shutil,time
from pathlib import Path
from .manifests import sha256_file,atomic_json
class StorageBackend(abc.ABC):
    @abc.abstractmethod
    def upload_shard(self,path,key): ...
    @abc.abstractmethod
    def verify_upload(self,key,checksum): ...
    @abc.abstractmethod
    def list_shards(self): ...
    @abc.abstractmethod
    def read_manifest(self,key): ...
    @abc.abstractmethod
    def write_manifest(self,key,value): ...
    def restore_checkpoint(self,key): return self.read_manifest(key)
    @abc.abstractmethod
    def used_bytes(self): ...
class ExternalSSDBackend(StorageBackend):
    def __init__(self,root,quota,min_free=0):
        self.root=Path(root).resolve();self.quota=quota;self.min_free=min_free
        self.root.mkdir(parents=True,exist_ok=True)
    def path(self,key):
        if Path(key).name!=key or key in ('.','..'): raise ValueError("unsafe storage key")
        p=self.root/key
        if p.is_symlink(): raise ValueError("symlink destination forbidden")
        return p
    def used_bytes(self): return sum(p.stat().st_size for p in self.root.rglob('*') if p.is_file())
    def budget(self,n):
        if self.used_bytes()+n>self.quota or shutil.disk_usage(self.root).free-n<self.min_free:
            raise RuntimeError("destination quota/free-space limit")
    def upload_shard(self,path,key):
        target=self.path(key);checksum=sha256_file(path)
        if target.exists():
            if sha256_file(target)!=checksum: raise RuntimeError("immutable object conflict")
            return
        self.budget(Path(path).stat().st_size+4096)
        tmp=self.path(key+'.partial')
        with open(path,'rb') as src,open(tmp,'wb') as dst:
            shutil.copyfileobj(src,dst,length=1024*1024);dst.flush();os.fsync(dst.fileno())
        os.replace(tmp,target)
    def verify_upload(self,key,checksum):
        p=self.path(key);return p.exists() and sha256_file(p)==checksum
    def list_shards(self): return (p.name for p in self.root.glob('*.parquet'))
    def read_manifest(self,key): return json.loads(self.path(key).read_text())
    def write_manifest(self,key,value):
        self.budget(len(json.dumps(value).encode())*2+4096);atomic_json(self.path(key),value)
class MockBackend(ExternalSSDBackend):
    """Filesystem-backed test double. Tests can corrupt bytes to exercise cleanup safety."""
class S3Backend(StorageBackend):
    def __init__(self,s):
        import boto3
        from urllib.parse import urlparse
        u=urlparse(s.destination)
        if u.scheme!='s3' or not u.netloc: raise ValueError("use s3://bucket/prefix")
        self.client=boto3.client('s3',endpoint_url=s.s3_endpoint)
        self.bucket=u.netloc;self.prefix=u.path.strip('/');self.quota=s.remote_quota_bytes
    def key(self,k): return '/'.join(x for x in (self.prefix,k) if x)
    def used_bytes(self):
        return sum(o['Size'] for page in self.client.get_paginator('list_objects_v2').paginate(Bucket=self.bucket,Prefix=self.prefix+'/') for o in page.get('Contents',[]))
    def upload_shard(self,path,key):
        if self.used_bytes()+Path(path).stat().st_size+65536>self.quota: raise RuntimeError("configured S3 quota exhausted")
        from boto3.s3.transfer import TransferConfig
        self.client.upload_file(str(path),self.bucket,self.key(key),Config=TransferConfig(max_concurrency=1,use_threads=False))
    def verify_upload(self,key,checksum):
        body=self.client.get_object(Bucket=self.bucket,Key=self.key(key))['Body'];h=hashlib.sha256()
        try:
            for block in iter(lambda:body.read(1024*1024),b''): h.update(block)
        finally: body.close()
        return h.hexdigest()==checksum
    def list_shards(self):
        for page in self.client.get_paginator('list_objects_v2').paginate(Bucket=self.bucket,Prefix=self.prefix+'/'):
            for obj in page.get('Contents',[]):
                if obj['Key'].endswith('.parquet'): yield obj['Key'].split('/')[-1]
    def read_manifest(self,key):
        body=self.client.get_object(Bucket=self.bucket,Key=self.key(key))['Body']
        try: return json.loads(body.read(1024*1024))
        finally: body.close()
    def write_manifest(self,key,value):
        data=json.dumps(value).encode()
        if self.used_bytes()+len(data)>self.quota: raise RuntimeError("configured S3 quota exhausted")
        self.client.put_object(Bucket=self.bucket,Key=self.key(key),Body=data)
class HFBackend(StorageBackend):
    def __init__(self,s):
        from huggingface_hub import HfApi
        self.api=HfApi(token=os.environ.get('HF_TOKEN'));self.repo=s.destination;self.quota=s.remote_quota_bytes
    def used_bytes(self):
        return sum((entry.size or 0) for entry in self.api.list_repo_tree(self.repo,repo_type='dataset',recursive=True) if hasattr(entry,'size'))
    def upload_shard(self,path,key):
        if self.used_bytes()+Path(path).stat().st_size+65536>self.quota: raise RuntimeError("configured HF quota exhausted")
        self.api.upload_file(path_or_fileobj=str(path),path_in_repo=key,repo_id=self.repo,repo_type='dataset')
    def stream(self,key):
        from huggingface_hub import hf_hub_url
        import urllib.request
        url=hf_hub_url(self.repo,key,repo_type='dataset')
        headers={'Authorization':'Bearer '+os.environ['HF_TOKEN']} if os.environ.get('HF_TOKEN') else {}
        return urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=60)
    def verify_upload(self,key,checksum):
        h=hashlib.sha256()
        with self.stream(key) as f:
            for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
        return h.hexdigest()==checksum
    def list_shards(self): return (p for p in self.api.list_repo_files(self.repo,repo_type='dataset') if p.endswith('.parquet'))
    def read_manifest(self,key):
        with self.stream(key) as f: return json.loads(f.read(1024*1024))
    def write_manifest(self,key,value):
        data=json.dumps(value).encode()
        if self.used_bytes()+len(data)>self.quota: raise RuntimeError("configured HF quota exhausted")
        self.api.upload_file(path_or_fileobj=data,path_in_repo=key,repo_id=self.repo,repo_type='dataset')

def backend_for(s):
    if not s.allow_upload or s.backend=='none': raise RuntimeError("upload disabled; configure finite destination quota and allow_upload explicitly")
    if s.backend=='external':
        target=Path(s.destination).resolve();workspace=s.workspace.resolve()
        if target.is_relative_to(workspace) or workspace.is_relative_to(target): raise ValueError("destination must be outside workspace")
        return ExternalSSDBackend(target,s.remote_quota_bytes,s.min_free_bytes)
    return S3Backend(s) if s.backend=='s3' else HFBackend(s)

def upload_pending(s,state,guard,backend=None):
    backend=backend or backend_for(s)
    uploaded=0
    for shard in list(state.shards()):
        guard.validate_write_budget(65536)
        path=s.workspace/'shards'/shard['name']
        if shard['uploaded']:
            if not backend.verify_upload(shard['name'],shard['checksum']): raise RuntimeError("previously uploaded shard lost/corrupt; cleanup refused")
            continue
        if sha256_file(path)!=shard['checksum']: raise ValueError("local shard checksum mismatch")
        error=None
        for attempt in range(3):
            try:
                backend.upload_shard(path,shard['name'])
                if not backend.verify_upload(shard['name'],shard['checksum']): raise ValueError("remote checksum mismatch")
                m=shard['manifest'];backend.write_manifest(shard['name']+'.json',m)
                if backend.restore_checkpoint(shard['name']+'.json')!=m: raise ValueError("remote manifest mismatch")
                state.db.execute('UPDATE shards SET uploaded=1 WHERE name=?',(shard['name'],));state.db.commit()
                uploaded+=1;error=None;break
            except Exception as exc:
                error=exc
                if attempt<2: time.sleep(0.1*(attempt+1))
        if error: raise error
        # Completed local shard is retained in v1. No automatic removal of the final copy.
    return uploaded
