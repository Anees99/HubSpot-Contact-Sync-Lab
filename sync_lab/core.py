"""Prepare reviewable HubSpot contact upserts; no network or CRM mutation."""
import csv
import hashlib
import io
import json
import re
from collections import Counter
FIELDS={'external_id','email','firstname','lastname','phone'}
PROPERTY='portfolio_external_id'

def clean(row):
    if not isinstance(row,dict) or set(row)-FIELDS:raise ValueError('Unknown input columns')
    out={}
    for k,v in row.items():
        if not isinstance(v,str) or len(v)>250:raise ValueError('Invalid field value')
        out[k]=v.strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',out.get('external_id','')):raise ValueError('Invalid external ID')
    email=out.get('email','').lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):raise ValueError('Invalid email')
    out['email']=email
    if out.get('phone'):
        phone=re.sub(r'[ ()-]','',out['phone'])
        if not re.fullmatch(r'\+[1-9]\d{7,14}',phone):raise ValueError('Phone must include country code')
        out['phone']=phone
    return out

def read_csv(content):
    reader=csv.DictReader(io.StringIO(content))
    if not reader.fieldnames or len(set(reader.fieldnames))!=len(reader.fieldnames):raise ValueError('Duplicate or missing CSV headers')
    if not {'external_id','email'}<=set(reader.fieldnames) or set(reader.fieldnames)-FIELDS:raise ValueError('Invalid CSV headers')
    return list(reader)

def plan(rows,batch_size=100):
    if type(batch_size)!=int or not 1<=batch_size<=100:raise ValueError('Batch size must be 1-100')
    if not isinstance(rows,list) or len(rows)>10000:raise ValueError('Maximum 10000 input rows')
    valid=[];rejected=[]
    for line,row in enumerate(rows,2):
        try:valid.append((line,clean(row)))
        except ValueError as e:rejected.append({'row':line,'reason':str(e)})
    # Any conflicting external ID or email quarantines every involved valid row.
    ids={};emails={}
    for _,row in valid:
        ids.setdefault(row['external_id'],set()).add(json.dumps(row,sort_keys=True))
        emails.setdefault(row['email'],set()).add(row['external_id'])
    accepted=[];seen=set();duplicates=0
    for line,row in valid:
        if len(ids[row['external_id']])>1 or len(emails[row['email']])>1:
            rejected.append({'row':line,'reason':'Conflicting identity; manual review required'});continue
        if row['external_id'] in seen:duplicates+=1;continue
        seen.add(row['external_id'])
        props={k:v for k,v in row.items() if k!='external_id' and v}
        props[PROPERTY]=row['external_id']
        accepted.append({'id':row['external_id'],'idProperty':PROPERTY,'properties':props})
    batches=[{'inputs':accepted[i:i+batch_size]} for i in range(0,len(accepted),batch_size)]
    report={'mode':'dry-run','schema_version':'1','endpoint':'https://api.hubapi.com/crm/v3/objects/contacts/batch/upsert',
        'required_unique_property':PROPERTY,'batches':batches,'rejected':rejected,
        'summary':{'input_rows':len(rows),'planned_contacts':len(accepted),'duplicate_rows_skipped':duplicates,'rejected_rows':len(rejected)}}
    report['plan_sha256']=hashlib.sha256(json.dumps(report,sort_keys=True).encode()).hexdigest()
    return report

def request_contract(batch):
    if not isinstance(batch,dict) or set(batch)!={'inputs'} or not 1<=len(batch['inputs'])<=100:raise ValueError('Invalid batch')
    return {'method':'POST','url':'https://api.hubapi.com/crm/v3/objects/contacts/batch/upsert',
        'headers':{'Authorization':'Bearer <PRIVATE_APP_TOKEN>','Content-Type':'application/json'},'json':batch}

def reconcile(batch,response):
    expected={x['id'] for x in batch['inputs']}
    if not isinstance(response,dict):raise ValueError('Invalid response')
    rows=response.get('results',[])
    if not isinstance(rows,list):raise ValueError('Invalid response results')
    counts=Counter();unexpected=[]
    for row in rows:
        if not isinstance(row,dict):raise ValueError('Invalid result item')
        identity=row.get('properties',{}).get(PROPERTY)
        if identity not in expected:unexpected.append(identity)
        elif row.get('id'):counts[identity]+=1
    # Do not mark a partial, pending, duplicate or error response as complete success.
    success=sorted(k for k,v in counts.items() if v==1) if response.get('status')=='COMPLETE' and not response.get('errors') and not unexpected else []
    return {'confirmed':success,'needs_review':sorted(expected-set(success)),'unexpected_result_ids':unexpected,
        'provider_status':response.get('status','unknown'),'has_errors':bool(response.get('errors'))}

def retry_policy(status,attempt,retry_after=None):
    if type(attempt)!=int or not 1<=attempt<=3:raise ValueError('Attempt must be 1-3')
    if status not in (408,429,500,502,503,504) or attempt==3:return {'retry':False,'delay_seconds':None}
    delay=min(2**attempt,30)
    if retry_after is not None:
        if type(retry_after) not in (int,float) or not 0<=retry_after<=300:raise ValueError('Retry-After must be 0-300 seconds')
        delay=max(delay,retry_after)
    return {'retry':True,'delay_seconds':delay}
