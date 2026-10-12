import argparse,json,sys,platform
from pathlib import Path
from .settings import Settings
from .storage_guard import StorageGuard,PipelinePaused
from .pipeline import initialize,run,validate_shards
from .checkpoint import State
from .metrics import report

def main(argv=None):
    parser=argparse.ArgumentParser(description='FullStackOps bounded pilot builder')
    parser.add_argument('--config',default='config/settings.yaml')
    commands=parser.add_subparsers(dest='command',required=True)
    for name in ('doctor','init','validate','upload','resume','status','storage-report','benchmark'):
        commands.add_parser(name)
    for name in ('collect','generate','build','dry-run'):
        p=commands.add_parser(name);p.add_argument('--limit',type=int,default=1000)
    args=parser.parse_args(argv)
    try:
        s=Settings.load(args.config);guard=StorageGuard(s)
        if args.command=='doctor':
            result={'python':platform.python_version(),'platform':platform.platform(),'storage':guard.generate_storage_report(),
                    'backend':s.backend,'upload_enabled':s.allow_upload}
            try: guard.validate_write_budget(2*1024**2);result['safe_to_start']=True
            except PipelinePaused as exc: result['safe_to_start']=False;result['reason']=str(exc)
        elif args.command=='dry-run':
            if not 1<=args.limit<=s.max_job_candidates: raise ValueError('limit outside bounded job cap')
            result={'candidates':args.limit,'estimated_max_batch_write_bytes':guard.estimate_operation_size(s.row_group_records),
                    'storage':guard.generate_storage_report(),'writes_performed':False}
        elif args.command=='init':initialize(s);result={'initialized':str(s.workspace)}
        elif args.command in ('generate','build','collect','resume'):
            result=run(s,getattr(args,'limit',1000),'collect' if args.command=='collect' else 'generate',resume=args.command=='resume')
        elif args.command=='validate':result=validate_shards(s)
        elif args.command=='benchmark':
            from .generator import CATALOG,generate_one
            from .validator import validate_record
            from .normalizer import split_for
            held=[i for i in range(len(CATALOG)) if split_for(f'policy-{i:02d}',s.seed)=='heldout']
            for i in held: validate_record(generate_one(i,s.seed))
            result={'heldout_families_checked':len(held),'policy_checks_passed':len(held),'runtime_tests':0,
                    'scope':'Validator self-check on held-out template families, not an LLM capability benchmark'}
        else:
            if not (s.workspace/'state.sqlite').exists(): raise ValueError('initialize or build first')
            state=State(s.workspace)
            try:
                if args.command=='upload':
                    from .uploader import upload_pending
                    result={'uploaded_shards':upload_pending(s,state,guard)}
                else:result=report(s,state)
            finally:state.close()
        print(json.dumps(result,indent=2,default=str))
        if result.get('current_job',{} ) and result['current_job']['status']=='paused':return 2
        return 0
    except (ValueError,RuntimeError,OSError,MemoryError) as exc:
        print(json.dumps({'error':str(exc),'data_preserved':True}),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
