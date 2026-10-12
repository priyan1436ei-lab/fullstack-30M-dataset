"""Finite original policy scenarios. No network, model calls or repository execution."""
import json, hashlib
import yaml
from .schema import Record,now
from .normalizer import content_hash,split_for
from .validator import check_policy
# category, framework, key, expected values, faulty values, meaningful task context
CATALOG = [
("fullstack", "FastAPI", "service.port", [8000,8080,9000], [0,-1], "Align the API listening port with the declared ingress target"),
("fullstack", "Express", "service.bind", ["0.0.0.0","::"], ["127.0.0.1","localhost"], "Expose the service to its container network"),
("fullstack", "Django", "database.engine", ["postgresql","mysql","sqlite"], ["unknown","disabled"], "Select the documented database engine"),
("fullstack", "Spring Boot", "health.path", ["/actuator/health","/health","/ready"], ["/missing","/invalid"], "Align the probe endpoint with the application contract"),
("fullstack", "Next.js", "build.output", ["standalone","export"], ["unsupported","empty"], "Use the requested deployment artifact mode"),
("fullstack", "Go", "service.shutdown_seconds", [10,20,30], [0,-1], "Configure the graceful shutdown window required by the load balancer"),
("fullstack", ".NET", "service.environment", ["Production","Staging"], ["Development","Unknown"], "Select the requested server environment"),
("fullstack", "Vue", "build.base", ["/portal/","/dashboard/","/app/"], ["/wrong/","/invalid/"], "Align the asset prefix with the published route"),
("docker", "Docker", "container.user", ["app","node","nobody"], ["root","administrator"], "Use the specified unprivileged runtime identity"),
("docker", "Compose", "container.restart", ["unless-stopped","on-failure","always"], ["invalid","disabled"], "Apply the requested container restart policy"),
("docker", "Docker", "container.port", [3000,8080,5000], [0,-1], "Match the exposed service port to the application listener"),
("docker", "Compose", "health.interval_seconds", [10,20,30], [0,-1], "Set a positive probe interval matching the service contract"),
("docker", "Docker", "build.stage", ["runtime","production","runner"], ["builder","invalid"], "Select the intended minimal runtime stage"),
("docker", "Compose", "volume.read_only", [True], [False], "Protect the mounted configuration from runtime writes"),
("docker", "Compose", "container.init", [True], [False], "Enable process reaping for the service"),
("docker", "Docker", "container.memory_mb", [128,256,512], [0,-1], "Apply the approved memory ceiling"),
("cicd", "GitHub Actions", "permissions.contents", ["read"], ["write","admin"], "Limit the build token to read access"),
("cicd", "GitLab CI", "job.timeout_minutes", [5,10,20], [0,-1], "Bound the job by the requested execution timeout"),
("cicd", "Jenkins", "artifact.retention_days", [7,14,30], [0,-1], "Apply the specified artifact retention period"),
("cicd", "GitHub Actions", "job.cancel_in_progress", [True], [False], "Cancel obsolete builds of the same branch"),
("cicd", "GitLab CI", "release.manual_approval", [True], [False], "Require approval for the protected release stage"),
("cicd", "Jenkins", "test.fail_on_error", [True], [False], "Block publication when tests fail"),
("cicd", "GitHub Actions", "checkout.fetch_depth", [0,1,2], [-1,-2], "Configure history depth for the specified versioning strategy"),
("cicd", "GitLab CI", "cache.policy", ["pull","pull-push","push"], ["invalid","none"], "Apply the requested dependency cache policy"),
("cloud", "AWS", "service.min_replicas", [1,2,3], [0,-1], "Maintain the requested availability floor"),
("cloud", "Azure", "health.protocol", ["HTTP","HTTPS","TCP"], ["FTP","INVALID"], "Use the service's documented probe protocol"),
("cloud", "Google Cloud", "service.concurrency", [20,40,80], [0,-1], "Bound concurrent requests per instance"),
("cloud", "Cloudflare", "runtime.compatibility_date", ["2024-01-01","2025-01-01","2026-01-01"], ["invalid","unknown"], "Set the reviewed runtime compatibility date"),
("cloud", "Vercel", "build.output_directory", ["dist","build","public"], ["missing","invalid"], "Align output configuration with the generated artifact"),
("cloud", "AWS", "service.max_replicas", [3,5,10], [0,-1], "Set the approved scaling ceiling"),
("cloud", "Azure", "logging.level", ["INFO","WARNING","ERROR"], ["INVALID","TRACEALL"], "Select the reviewed production log verbosity"),
("cloud", "Google Cloud", "service.timeout_seconds", [30,60,120], [0,-1], "Set the bounded request deadline"),
("errors", "Node.js", "service.entrypoint", ["server.js","app.js","index.js"], ["missing.js","invalid.js"], "Point startup to the documented application entrypoint"),
("errors", "PostgreSQL", "database.port", [5432,5433,6432], [0,-1], "Align database connection settings with the test service"),
("errors", "FastAPI", "service.workers", [1,2,4], [0,-1], "Restore the supported worker count"),
("errors", "Redis", "cache.port", [6379,6380,6381], [0,-1], "Align cache connectivity with the local service"),
("errors", "Node.js", "build.command", ["npm run build","pnpm build","yarn build"], ["npm run missing","invalid"], "Restore the declared build command without executing it"),
("errors", "Django", "database.pool_size", [5,10,20], [0,-1], "Restore the bounded connection pool"),
("errors", "Spring Boot", "service.profile", ["prod","staging","test"], ["missing","invalid"], "Select the documented active application profile"),
("errors", "Go", "health.timeout_seconds", [2,5,10], [0,-1], "Restore the approved probe deadline"),
("infra", "Kubernetes", "deployment.replicas", [1,2,3], [0,-1], "Match replicas to the availability requirement"),
("infra", "Helm", "service.type", ["ClusterIP","NodePort","LoadBalancer"], ["Unknown","Invalid"], "Use the requested Kubernetes service exposure type"),
("infra", "Terraform", "resource.prevent_destroy", [True], [False], "Retain the data resource destruction guard"),
("infra", "OpenTofu", "state.locking", [True], [False], "Enable concurrent state modification protection"),
("infra", "Ansible", "play.serial", [1,2,3], [0,-1], "Bound rolling-update batch size"),
("infra", "Kubernetes", "pod.run_as_non_root", [True], [False], "Enforce the non-root workload policy"),
("infra", "Helm", "probe.initial_delay_seconds", [5,10,20], [-1,-2], "Allow the declared startup warm-up time"),
("infra", "Terraform", "resource.encryption", [True], [False], "Enable the specified at-rest encryption policy"),
("security", "Monitoring", "alert.duration_minutes", [1,5,10], [0,-1], "Set the approved sustained-failure alert window"),
("security", "Recovery", "backup.retention_days", [7,14,30], [0,-1], "Restore the documented backup retention policy"),
("security", "Recovery", "rollback.approval", [True], [False], "Require approval for the state-changing recovery action"),
("security", "Monitoring", "logging.redact_credentials", [True], [False], "Enable credential redaction in the logging policy"),
("security", "Security", "network.public_database", [False], [True], "Restrict database access to the private network"),
("security", "Recovery", "restore.verify_checksum", [True], [False], "Require restored backup integrity verification"),
("security", "Security", "tls.minimum_version", ["1.2","1.3"], ["1.0","1.1"], "Set the minimum TLS version in the approved policy"),
("security", "Monitoring", "metrics.interval_seconds", [15,30,60], [0,-1], "Set a bounded metrics collection interval"),
]
# 24 bounded parameter combinations per family, not a 30M template multiplier.
PROFILES=[("dev",1,64),("staging",2,128),("production",3,256),("production",4,512)]
MAX_SYNTHETIC=len(CATALOG)*24

def generate_one(index,seed=42):
    if not 0<=index<MAX_SYNTHETIC: raise ValueError("finite catalog exhausted; add independent task families before scaling")
    if index >= 875:
        from .execution import generate_executable
        return generate_executable(index,seed)
    family=index%len(CATALOG); variant=index//len(CATALOG)
    cat,framework,key,valid,bad,description=CATALOG[family]
    # Parameters change operating requirements, input and expected output; counts still disclose family concentration.
    env,replicas,memory=PROFILES[variant%4]
    expected=valid[(variant//4)%len(valid)]; wrong=bad[(variant//12)%len(bad)]
    context={"environment":env,"replicas":replicas,"memory_mb":memory,
             "rollout":"rolling" if variant%2 else "blue-green", "health":"ready" if variant%3 else "live",
             "request_budget_per_second":[50,100,200,500,1000,2000][variant//4]}
    base={"context":context};cursor=base
    parts=key.split('.')
    for part in parts[:-1]: cursor=cursor.setdefault(part,{})
    cursor[parts[-1]]=expected
    good=yaml.safe_dump(base,sort_keys=True)
    cursor[parts[-1]]=wrong
    broken=yaml.safe_dump(base,sort_keys=True)
    template=f"policy-{family:02d}"
    lineage=template # Every parameterization of one template remains in exactly one split.
    rule=json.dumps(dict(key=key,expected=expected),sort_keys=True)
    results=[];actions=[]
    for step,(phase,content) in enumerate((("baseline",good),("fault",broken),("fixed",good)),1):
        code,out=check_policy(content,key,expected)
        command=f"internal.check_policy:{key}"
        results.append(dict(phase=phase,command=command,exit_code=code,output=out,verification_kind="static_policy"))
        actions.append(dict(step_number=step,tool_name="internal.check_policy",tool_arguments=json.dumps({"phase":phase,"key":key,"expected":expected}),
                            observed_output=out,exit_code=code,action_result="pass" if code==0 else "fail",
                            next_action="inject controlled fault" if phase=="baseline" else "apply supplied minimal fix" if phase=="fault" else "finish"))
    time=now()
    r=Record(record_id=hashlib.sha256(f"v1:{seed}:{index}".encode()).hexdigest(),task_category=cat,task_subcategory=key,
        programming_language="YAML",framework=framework,difficulty="easy",
        instruction=f"{description}. Environment: {env}; replicas: {replicas}; memory: {memory} MiB. Required {key}: {expected!r}.",
        environment={"validator":"internal policy checker","network":"disabled","execution":"in-process trusted validator"},
        repository_context=rule,input_files=[dict(path="service-policy.yaml",content=broken)],observations=[results[1]['output']],error_logs=[results[1]['output']],
        agent_actions=actions,expected_behavior=f"Policy {key} must equal {expected!r}; runtime behavior remains untested.",
        generated_patch=[dict(path="service-policy.yaml",content=good)],test_commands=[results[0]['command']],test_results=results,
        verification_status="static_validated",quality_state="VALIDATED",quality_score=0.65,
        source_type="original_synthetic",source_license="MIT",source_reference="original://fullstackops/v1",source_commit="catalog-v1",
        provenance=dict(source_url="original://fullstackops/v1",repository_identifier="fullstackops-original-policies",
            commit_revision="catalog-v1",file_path="service-policy.yaml",attribution="FullStackOps contributors",
            collected_at=time,redistribution_allowed=True,provenance_category="original_synthetic",template_id=template,
            mutation_id=f"replace:{key}",source_family=template,lineage=lineage),
        created_at=time,content_hash="",record_split=split_for(lineage,seed))
    r.content_hash=content_hash(r)
    return r

def generate(start,limit,seed=42):
    for i in range(start,min(start+limit,MAX_SYNTHETIC)): yield generate_one(i,seed)
