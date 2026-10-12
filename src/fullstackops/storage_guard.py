import os, shutil
from pathlib import Path
import psutil
def process_rss():
    # /proc/self is namespace-correct even when numeric PID lookups are not.
    if os.name=='posix' and Path('/proc/self/status').exists():
        for line in Path('/proc/self/status').read_text().splitlines():
            if line.startswith('VmRSS:'): return int(line.split()[1])*1024
    try: return psutil.Process().memory_info().rss
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        raise PipelinePaused('process memory accounting unavailable')

class PipelinePaused(RuntimeError):
    """A bounded operation cannot safely proceed. Committed shards remain intact."""
class StorageGuard:
    def __init__(self, settings): self.s = settings
    def anchor(self):
        p=self.s.workspace.resolve()
        while not p.exists(): p=p.parent
        return p
    def check_free_space(self): return shutil.disk_usage(self.anchor()).free
    def check_workspace_size(self):
        total=0
        roots=[self.s.workspace]+[self.s.workspace.parent/name for name in ('.venv','.pytest_cache','build','dist','logs','reports')]
        for root in roots:
            if not root.exists() or root==self.s.workspace and not self.s.workspace.exists(): continue
            if root.is_symlink(): raise PipelinePaused('controlled path is a symlink')
            for base, dirs, files in os.walk(root, followlinks=False):
                dirs[:]=[d for d in dirs if not (Path(base)/d).is_symlink()]
                for f in files:
                    p=Path(base)/f
                    if p.is_symlink(): raise PipelinePaused("workspace contains symlink")
                    total+=p.stat().st_size
        return total
    def temp_size(self):
        p=self.s.workspace/'staging'
        return sum(f.stat().st_size for f in p.rglob('*') if f.is_file()) if p.exists() else 0
    def estimate_operation_size(self, records=1):
        return records*self.s.max_record_bytes*2+2*1024**2
    def validate_write_budget(self, expected=0, temporary=0):
        p=self.s.workspace.absolute()
        if any(q.is_symlink() for q in [p,*p.parents]):
            raise PipelinePaused("workspace or ancestor is a symlink")
        if self.check_free_space()-expected < self.s.min_free_bytes:
            raise PipelinePaused("free disk reserve would fall below configured minimum")
        if self.check_workspace_size()+expected >= self.s.max_workspace_bytes:
            raise PipelinePaused("workspace budget reached")
        if self.temp_size()+temporary >= self.s.max_temp_bytes:
            raise PipelinePaused("temporary storage budget reached")
        if psutil.virtual_memory().available < self.s.min_available_ram_bytes:
            raise PipelinePaused("system RAM pressure")
        if process_rss() > self.s.memory_bytes:
            raise PipelinePaused("process memory budget reached")
        db=self.s.workspace/'state.sqlite'
        metadata=sum(p.stat().st_size for p in self.s.workspace.glob('state.sqlite*'))
        if metadata >= self.s.metadata_bytes:
            raise PipelinePaused("metadata limit; archive state before scaling")
    def pause_pipeline(self, reason): raise PipelinePaused(reason)
    def cleanup_verified_temporary_files(self, path, checksum, backend):
        path=Path(path).resolve()
        staging=(self.s.workspace/'staging').resolve()
        if not path.is_relative_to(staging): raise ValueError("only staging copies can be cleaned")
        if not backend.verify_upload(path.name, checksum): raise ValueError("remote integrity not verified")
        path.unlink()
    def generate_storage_report(self):
        return dict(free_bytes=self.check_free_space(), workspace_bytes=self.check_workspace_size(),
                    temporary_bytes=self.temp_size(), process_ram_bytes=process_rss(),
                    available_ram_bytes=psutil.virtual_memory().available,
                    workspace_limit_bytes=self.s.max_workspace_bytes, free_reserve_bytes=self.s.min_free_bytes)
