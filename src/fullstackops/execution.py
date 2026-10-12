"""Run only this module's trusted, finite arithmetic expressions, never repository code.
No imports, shell, file access, network, subprocess, user expressions or loops.
The expression whitelist is an isolation boundary for these original numerical tasks.
It is NOT a general-purpose sandbox for arbitrary Python.
"""
import json,hashlib
from .schema import Record,now
from .normalizer import content_hash,split_for
# correct code, controlled fault, independent oracle, task category, task description
CASES=[
 ('(requests + capacity - 1) // capacity','requests // capacity',lambda v:(v['requests']//v['capacity'])+(v['requests']%v['capacity']!=0),'cloud','Calculate the minimum whole replicas needed for the incoming request rate'),
 ('min(maximum, base * attempt)','maximum + base * attempt',lambda v:v['maximum'] if v['base']*v['attempt']>v['maximum'] else v['base']*v['attempt'],'errors','Cap the retry delay at the configured maximum'),
 ('budget // workers','budget * workers',lambda v:divmod(v['budget'],v['workers'])[0],'docker','Divide the container memory budget equally among worker processes'),
 ('min(requested, available)','max(requested, available)',lambda v:v['requested'] if v['requested']<v['available'] else v['available'],'infra','Bound rolling-update batch size by available capacity'),
 ('used + incoming <= limit','used + incoming < limit',lambda v:not(v['used']+v['incoming']>v['limit']),'security','Allow a bounded write exactly at the permitted byte ceiling'),
 ('elapsed >= deadline','elapsed > deadline',lambda v:not(v['elapsed']<v['deadline']),'cicd','Trigger a job timeout exactly at the deadline'),
 ('healthy >= required','healthy > required',lambda v:not(v['healthy']<v['required']),'fullstack','Accept readiness when the healthy replica threshold is met'),
]

def parameters(family,variant):
    n=variant+1
    values=[dict(requests=(10+n)*(3+n%4)+1,capacity=10+n),dict(maximum=100+n,base=10+n,attempt=3+n%5),
       dict(budget=1024+16*n,workers=2+n%4),dict(requested=8+n,available=3+n%3),
       dict(used=100+n,incoming=20+n,limit=120+2*n),dict(elapsed=30+n,deadline=30+n),
       dict(healthy=2+n,required=2+n)]
    return values[family]

def check_trusted(family,variant,phase):
    # Source text comes only from CASES; input values come only from parameters().
    good,bad,oracle,category,title=CASES[family]
    expression=bad if phase=='fault' else good
    values=parameters(family,variant)
    actual=eval(compile(expression,'<original-trusted-expression>','eval'),{'__builtins__':{},'min':min,'max':max},values)
    expected=oracle(values)
    code=0 if actual==expected else 1
    return code,json.dumps(dict(actual=actual,expected=expected,passed=actual==expected),sort_keys=True)

def generate_executable(index,seed):
    position=index-875;family=position%len(CASES);variant=position//len(CASES)
    good,bad,oracle,category,title=CASES[family];values=parameters(family,variant)
    results=[];actions=[]
    for step,phase in enumerate(('baseline','fault','fixed'),1):
        code,out=check_trusted(family,variant,phase)
        results.append(dict(phase=phase,command='internal.trusted_expression',exit_code=code,output=out,verification_kind='trusted_python'))
        actions.append(dict(step_number=step,tool_name='internal.trusted_expression',tool_arguments=json.dumps(dict(family=family,variant=variant,phase=phase)),
           observed_output=out,exit_code=code,action_result='pass' if code==0 else 'fail',next_action='inject fault' if phase=='baseline' else 'apply minimal correction' if phase=='fault' else 'finish'))
    timestamp=now();template=f'python-{family:02d}'
    r=Record(record_id=hashlib.sha256(f'v1-exec:{seed}:{index}'.encode()).hexdigest(),task_category=category,task_subcategory='bounded-resource-calculation',
       programming_language='Python',framework='standard-library',difficulty='easy',instruction=f'{title}. Inputs: {json.dumps(values,sort_keys=True)}.',
       environment={'execution':'trusted arithmetic expression only','network':'disabled','files':'none'},repository_context=json.dumps(dict(family=family,variant=variant)),
       input_files=[dict(path='calculation.py',content=f'result = {bad}\n')],observations=[results[1]['output']],error_logs=[results[1]['output']],agent_actions=actions,
       expected_behavior=f'Return {oracle(values)!r} for the supplied bounded numerical input. No service deployment is tested.',
       generated_patch=[dict(path='calculation.py',content=f'result = {good}\n')],test_commands=['internal.trusted_expression'],test_results=results,
       verification_status='runtime_verified',quality_state='VALIDATED',quality_score=0.8,source_type='original_synthetic',source_license='MIT',source_reference='original://fullstackops/v1',source_commit='catalog-v1',
       provenance=dict(source_url='original://fullstackops/v1',repository_identifier='fullstackops-original-policies',commit_revision='catalog-v1',file_path='calculation.py',
         attribution='FullStackOps contributors',collected_at=timestamp,redistribution_allowed=True,provenance_category='original_synthetic',template_id=template,
         mutation_id='arithmetic-boundary-fault',source_family=template,lineage=template),created_at=timestamp,content_hash='',record_split=split_for(template,seed))
    r.content_hash=content_hash(r);return r

def validate_execution(r):
    context=json.loads(r.repository_context);family=context['family'];variant=context['variant']
    if type(family)!=int or not 0<=family<len(CASES) or type(variant)!=int or not 0<=variant<1000:raise ValueError('unknown trusted scenario')
    good,bad,*_=CASES[family]
    if r.generated_patch[0].content!=f'result = {good}\n' or r.input_files[0].content!=f'result = {bad}\n':raise ValueError('code outside trusted catalog')
    for phase in ('baseline','fault','fixed'):
        code,out=check_trusted(family,variant,phase)
        t=next(x for x in r.test_results if x.phase==phase)
        if t.exit_code!=code or t.output!=out or t.verification_kind!='trusted_python':raise ValueError('fabricated runtime evidence')
