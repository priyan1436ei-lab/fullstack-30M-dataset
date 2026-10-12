import hashlib,json,os
from pathlib import Path

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''): h.update(block)
    return h.hexdigest()
def atomic_json(path,value,guard=None):
    p=Path(path);data=json.dumps(value,indent=2,sort_keys=True).encode()
    if guard: guard.validate_write_budget(len(data)*2+4096,len(data))
    tmp=p.with_suffix(p.suffix+'.partial')
    with open(tmp,'wb') as f: f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(tmp,p)
