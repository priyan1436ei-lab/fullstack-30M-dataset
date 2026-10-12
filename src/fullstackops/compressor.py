import json,os
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from .manifests import sha256_file,atomic_json
from .schema import Record
from .storage_guard import PipelinePaused
class Compressor:
    def __init__(self,settings,guard): self.s=settings;self.guard=guard
    def write(self,records,name,job):
        if not records: raise ValueError("empty shard")
        raw=sum(len(r.model_dump_json().encode()) for r in records)
        self.guard.validate_write_budget(raw*4+2*1024**2,raw*2)
        # JSON -> Arrow yields genuine nested structs, with a stable per-shard schema.
        # Each shard only contains one verification subset; no empty test structures inferred as null.
        table=pa.Table.from_pylist([r.model_dump() for r in records])
        metadata=dict(table.schema.metadata or {})
        metadata[b'fullstackops_job']=json.dumps(job).encode()
        table=table.replace_schema_metadata(metadata)
        sink=pa.BufferOutputStream()
        pq.write_table(table,sink,compression='zstd',compression_level=self.s.compression_level,
                       row_group_size=min(len(records),self.s.row_group_records))
        buf=sink.getvalue()
        if len(buf)>self.s.shard_bytes: raise PipelinePaused("compressed row group exceeds shard limit; reduce row_group_records")
        self.guard.validate_write_budget(len(buf)*2+4096,len(buf))
        tmp=self.s.workspace/'staging'/f'{name}.partial'
        final=self.s.workspace/'shards'/name
        with open(tmp,'wb') as f: f.write(buf);f.flush();os.fsync(f.fileno())
        # Verify before publishing; the tiny row group remains bounded.
        rows=pq.read_table(tmp).to_pylist()
        if len(rows)!=len(records): raise ValueError("Parquet row count mismatch")
        for original,row in zip(records,rows):
            restored=Record.model_validate(row)
            if restored.model_dump()!=original.model_dump(): raise ValueError("Parquet roundtrip mismatch")
        checksum=sha256_file(tmp)
        os.replace(tmp,final)
        manifest=dict(name=name,sha256=checksum,records=len(records),raw_bytes=raw,compressed_bytes=final.stat().st_size,
                      schema_version='1.0',job=job,verification_subset=records[0].verification_status,
                      splits=sorted({r.record_split for r in records}))
        atomic_json(self.s.workspace/'manifests'/f'{name}.json',manifest,self.guard)
        return manifest
