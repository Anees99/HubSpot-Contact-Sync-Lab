import argparse
import json
from pathlib import Path
from .core import plan,read_csv,reconcile
p=argparse.ArgumentParser(description='HubSpot contact synchronization dry-run planner')
s=p.add_subparsers(dest='command',required=True)
a=s.add_parser('plan');a.add_argument('csv');a.add_argument('--batch-size',type=int,default=100)
a=s.add_parser('reconcile');a.add_argument('plan');a.add_argument('response');a.add_argument('--batch',type=int,default=0)
a=p.parse_args()
if a.command=='plan':result=plan(read_csv(Path(a.csv).read_text(encoding='utf-8-sig')),a.batch_size)
else:
    report=json.loads(Path(a.plan).read_text());response=json.loads(Path(a.response).read_text())
    result=reconcile(report['batches'][a.batch],response)
print(json.dumps(result,indent=2,ensure_ascii=False))
