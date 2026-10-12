from pathlib import Path
import json,pyarrow.parquet as pq
path=next(Path('data/shards').glob('*.parquet'))
record=next(pq.ParquetFile(path).iter_batches(batch_size=1)).to_pylist()[0]
print(json.dumps(record,indent=2))
