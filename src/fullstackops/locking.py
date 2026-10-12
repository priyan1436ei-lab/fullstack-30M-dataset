"""Cross-platform single-writer lock; the process owns it until context exit."""
from contextlib import contextmanager
@contextmanager
def writer_lock(workspace):
    p=workspace/'.writer.lock'
    if p.is_symlink(): raise RuntimeError('symlink lock rejected')
    with p.open('a+b') as stream:
        stream.seek(0);stream.write(b'0');stream.flush();stream.seek(0)
        try:
            import os
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except (OSError,BlockingIOError) as exc: raise RuntimeError('another pipeline writer is active') from exc
        try: yield
        finally:
            if os.name=='nt':
                stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else: fcntl.flock(stream,fcntl.LOCK_UN)
