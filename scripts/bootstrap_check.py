import shutil,sys
from pathlib import Path
if sys.version_info < (3,11): raise SystemExit("Python 3.11+ required")
free=shutil.disk_usage(Path.cwd()).free
required=26*1024**3 # 25 GiB reserve + conservative 1 GiB setup allowance
print(f"Free disk: {free/1024**3:.2f} GiB; setup threshold: 26 GiB")
if free<required: raise SystemExit("Insufficient free space for safe dependency setup")
