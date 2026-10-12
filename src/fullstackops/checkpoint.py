import sqlite3,json
from .schema import now
class State:
    def __init__(self,workspace):
        self.path=workspace/'state.sqlite'
        self.db=sqlite3.connect(self.path)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript("""
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, mode TEXT NOT NULL, source_offset INTEGER NOT NULL,
 target INTEGER NOT NULL, status TEXT NOT NULL, last_error TEXT, updated_at TEXT NOT NULL, source_fingerprint TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS records(hash TEXT PRIMARY KEY,id TEXT UNIQUE NOT NULL,source_identity TEXT UNIQUE NOT NULL,
 family TEXT NOT NULL,split TEXT NOT NULL,shard TEXT NOT NULL,status TEXT NOT NULL,category TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS shards(name TEXT PRIMARY KEY,checksum TEXT NOT NULL,records INTEGER NOT NULL,bytes INTEGER NOT NULL,
 uploaded INTEGER NOT NULL DEFAULT 0,manifest TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS counters(name TEXT PRIMARY KEY,value INTEGER NOT NULL);
""")
    def count(self,name,n=1):
        self.db.execute('INSERT INTO counters VALUES (?,?) ON CONFLICT(name) DO UPDATE SET value=value+excluded.value',(name,n))
    def job(self):
        row=self.db.execute('SELECT * FROM jobs ORDER BY updated_at DESC LIMIT 1').fetchone()
        return dict(zip(('id','mode','source_offset','target','status','last_error','updated_at','source_fingerprint'),row)) if row else None
    def start(self,jid,mode,target,fingerprint):
        self.db.execute('INSERT INTO jobs VALUES (?,?,0,?,?,NULL,?,?)',(jid,mode,target,'running',now(),fingerprint));self.db.commit()
    def progress(self,jid,offset,status='running',error=None):
        self.db.execute('UPDATE jobs SET source_offset=?,status=?,last_error=?,updated_at=? WHERE id=?',(offset,status,error,now(),jid))
    def register(self,manifest,records):
        name=manifest['name']
        for r in records:
            identity=f"{r.source_reference}:{r.source_commit}:{r.record_id}"
            self.db.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?,?)',(r.content_hash,r.record_id,identity,
                r.provenance.source_family,r.record_split,name,r.verification_status,r.task_category))
        self.db.execute('INSERT INTO shards(name,checksum,records,bytes,manifest) VALUES (?,?,?,?,?)',
            (name,manifest['sha256'],manifest['records'],manifest['compressed_bytes'],json.dumps(manifest)))
    def shards(self):
        for name,checksum,records,size,uploaded,manifest in self.db.execute('SELECT * FROM shards ORDER BY name'):
            yield dict(name=name,checksum=checksum,records=records,bytes=size,uploaded=bool(uploaded),manifest=json.loads(manifest))
    def close(self):
        self.db.commit();self.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');self.db.close()
