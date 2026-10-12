from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, model_validator
import yaml
GIB = 1024 ** 3
class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace: Path = Path("data")
    max_workspace_bytes: int = 15 * GIB
    min_free_bytes: int = 25 * GIB
    max_temp_bytes: int = 5 * GIB
    memory_bytes: int = int(1.5 * GIB)
    min_available_ram_bytes: int = 256 * 1024 ** 2
    shard_bytes: int = Field(default=128 * 1024 ** 2, ge=65536, le=128 * 1024 ** 2)
    row_group_records: int = Field(default=64, ge=1, le=256)
    max_workers: int = Field(default=2, ge=1, le=2)
    metadata_bytes: int = 128 * 1024 ** 2
    max_record_bytes: int = 256 * 1024
    max_local_records: int = 10000
    max_job_candidates: int = 10000
    seed: int = 42
    compression_level: int = Field(default=3, ge=1, le=9)
    sources_file: Path = Path("config/sources.yaml")
    backend: str = "none"
    destination: str = ""
    remote_quota_bytes: int = 0
    allow_upload: bool = False
    s3_endpoint: str | None = None
    @model_validator(mode="after")
    def budgets(self):
        if min(self.max_workspace_bytes,self.min_free_bytes,self.max_temp_bytes,
               self.memory_bytes,self.metadata_bytes,self.max_record_bytes,self.max_local_records,
               self.max_job_candidates) <= 0:
            raise ValueError("budgets must be positive")
        if self.row_group_records * self.max_record_bytes * 8 > self.memory_bytes:
            raise ValueError("row-group buffer reserve exceeds memory budget")
        if self.backend not in ("none","external","s3","hf"):
            raise ValueError("unsupported backend")
        if self.backend != "none" and (not self.destination or self.remote_quota_bytes <= 0):
            raise ValueError("destination and finite remote quota required")
        return self
    @classmethod
    def load(cls, path):
        return cls.model_validate(yaml.safe_load(Path(path).read_text()) or {})
