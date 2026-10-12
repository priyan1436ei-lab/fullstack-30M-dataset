import hashlib,json
FIELDS=("task_category","task_subcategory","programming_language","framework","instruction",
        "input_files","generated_patch","expected_behavior")
def canonical_content(record):
    d=record.model_dump() if hasattr(record,"model_dump") else record
    # Whitespace-only variation does not create a new task identity.
    content={k:d[k] for k in FIELDS}
    for key in ("input_files","generated_patch"):
        content[key]=[{"path":f["path"],"content":"\n".join(x.rstrip() for x in f["content"].strip().splitlines())} for f in content[key]]
    return json.dumps(content,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def content_hash(record): return hashlib.sha256(canonical_content(record).encode()).hexdigest()
def split_for(lineage, seed):
    n=int(hashlib.sha256(f"{seed}:{lineage}".encode()).hexdigest()[:8],16)%100
    return "heldout" if n<5 else "test" if n<15 else "validation" if n<25 else "train"
