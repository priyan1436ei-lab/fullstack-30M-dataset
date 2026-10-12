from collections import Counter
import re
class Deduplicator:
    def __init__(self,state): self.state=state
    def is_duplicate(self,r):
        identity=f"{r.source_reference}:{r.source_commit}:{r.record_id}"
        return bool(self.state.db.execute('SELECT 1 FROM records WHERE hash=? OR id=? OR source_identity=?',
            (r.content_hash,r.record_id,identity)).fetchone())
    def check_split(self,r):
        row=self.state.db.execute('SELECT split FROM records WHERE family=? LIMIT 1',(r.provenance.source_family,)).fetchone()
        if row and row[0]!=r.record_split: raise ValueError("lineage split contamination")
    @staticmethod
    def near_duplicate_similarity(a,b):
        # Diagnostic only: template relatives are disclosed, not counted as independent novel tasks.
        x=set(re.findall(r'[a-z_]+',a.lower()));y=set(re.findall(r'[a-z_]+',b.lower()))
        return len(x&y)/max(1,len(x|y))
