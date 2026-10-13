"""Runnable local operator example; never modifies a product channel or repository."""
import csv
import json
import subprocess
import tempfile
from pathlib import Path
from agentic_portfolio.catalog_flow import Cases
from agentic_portfolio.engineering_flow import verify_change, git_revision
from agentic_portfolio.orchestrator import Queue

with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    repo=root/'repo';repo.mkdir()
    subprocess.run(['git','init','-q',str(repo)],check=True)
    subprocess.run(['git','-C',str(repo),'-c','user.name=Demo','-c',
                    'user.email=demo@example.com','commit','--allow-empty',
                    '-qm','initial'],check=True)
    queue=Queue(str(root/'queue.db'))
    sha=git_revision(str(repo))
    result=verify_change(queue,str(repo),sha,sha,
                         ('python3','-c','print("CI checks passed")'))
    queue.review(result.job_id,True,'QA reviewer','Independent test passed')
    print('ENGINEERING:',json.dumps({
        'revision':result.candidate,'status':result.status,
        'exit_code':result.exit_code,'ledger_valid':queue.verify_chain()}))
    columns=['sku','title','description','price','currency','availability','image_url']
    catalog=dict(zip(columns,['SKU-1','Device','Product text','100.00','USD','in stock','image.png']))
    page=dict(catalog,price='110.00')
    for name,row in [('catalog.csv',catalog),('channel.csv',page)]:
        with (root/name).open('w',newline='') as fp:
            writer=csv.DictWriter(fp,fieldnames=columns)
            writer.writeheader();writer.writerow(row)
    cases=Cases(str(root/'cases.db'))
    print('CATALOG:',json.dumps(cases.ingest(str(root/'catalog.csv'),str(root/'channel.csv')),indent=2))
