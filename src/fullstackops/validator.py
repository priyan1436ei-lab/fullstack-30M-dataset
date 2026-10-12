import ast,json,re
import yaml
from .schema import Record
from .normalizer import content_hash
LICENSES={"MIT","Apache-2.0","BSD-2-Clause","BSD-3-Clause","CC0-1.0"}
SECRET_PATTERNS=[r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----",r"AKIA[0-9A-Z]{16}",
    r"gh[pousr]_[A-Za-z0-9]{20,}",r"sk-[A-Za-z0-9]{20,}",
    r"(?i)(?:password|passwd|api[_-]?key|access[_-]?token|secret)\s*[=:]\s*['\"]?(?!\$|<|REDACTED|EXAMPLE|\s*['\"]?\s*$)[A-Za-z0-9+/._-]{8,}",
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",r"(?<!\d)(?:\+91[ -]?)?[6-9]\d{9}(?!\d)"]
def security_scan(text): return [p for p in SECRET_PATTERNS if re.search(p,text)]
def check_policy(content, key, expected):
    try:
        d=yaml.safe_load(content)
        value=d
        for part in key.split('.'): value=value[part]
        ok=type(value)==type(expected) and value==expected
        return (0 if ok else 1), (f"PASS: {key} matches expected configuration" if ok else f"FAIL: {key} differs from required configuration")
    except (yaml.YAMLError,KeyError,TypeError): return 1,f"FAIL: missing or malformed {key}"
def validate_record(value):
    r=Record.model_validate(value)
    if r.source_license not in LICENSES: raise ValueError("unapproved license")
    # Scan data content, excluding timestamps/hashes (which can look like phone numbers).
    text=json.dumps({k:getattr(r,k) if k not in ("input_files","generated_patch") else [f.model_dump() for f in getattr(r,k)]
                     for k in ("instruction","repository_context","observations","error_logs","input_files","generated_patch")})
    if security_scan(text): raise ValueError("secret or PII detected")
    for f in r.input_files+r.generated_patch:
        if f.path.startswith(('/', '\\')) or '..' in f.path.replace('\\','/').split('/'):
            raise ValueError("unsafe file path")
    if r.content_hash != content_hash(r): raise ValueError("content hash mismatch")
    if r.source_type=="original_synthetic" and r.verification_status=="static_validated":
        rule=json.loads(r.repository_context)
        for phase,files in (("baseline",r.generated_patch),("fault",r.input_files),("fixed",r.generated_patch)):
            code,out=check_policy(files[0].content,rule['key'],rule['expected'])
            evidence=next(t for t in r.test_results if t.phase==phase)
            if evidence.exit_code!=code or evidence.output!=out: raise ValueError("fabricated policy evidence")
        for action,result in zip(r.agent_actions,r.test_results):
            if action.exit_code!=result.exit_code or action.observed_output!=result.output:
                raise ValueError("trajectory evidence mismatch")
    if r.verification_status=="runtime_verified":
        if r.source_type!="original_synthetic": raise ValueError("untrusted execution forbidden")
        from .execution import validate_execution
        validate_execution(r)
    return r
