"""Strict JSON/CSV input, reproducible OMR snapshots, no remote calls."""
import csv,io,json
from finance import CORE,OPTIONAL,validate_period

def normalize_dataset(data):
    if not isinstance(data,dict) or not isinstance(data.get('periods'),list) or not data['periods']:raise ValueError('يلزم كائن JSON يحتوي قائمة periods غير فارغة.')
    if str(data.get('currency','OMR')).upper()!='OMR':raise ValueError('النسخة الحالية تدعم OMR فقط. لا تُجمع عملات مختلفة.')
    if len(data['periods'])>100:raise ValueError('الحد الأقصى 100 فترة.')
    seen=set();periods=[]
    for raw in data['periods']:
        if not isinstance(raw,dict):raise ValueError('كل فترة يجب أن تكون كائناً.')
        p=dict(raw);p['label']=str(p.get('label','')).strip()
        for k in (*CORE,*OPTIONAL):
            if k not in p or p[k] in ('',None):p[k]=None
            elif isinstance(p[k],str):
                try:p[k]=float(p[k].replace(',','').strip())
                except ValueError:raise ValueError(f'{k}: تعذر قراءة الرقم.')
        errors,_=validate_period(p)
        if errors:raise ValueError(p['label']+': '+' / '.join(errors))
        if p['label'] in seen:raise ValueError('أسماء الفترات يجب أن تكون فريدة.')
        seen.add(p['label']);periods.append(p)
    return {'company':str(data.get('company','Company'))[:120],'currency':'OMR','source':str(data.get('source','User input'))[:500],'periods':periods}

def load_bytes(blob,filename):
    if len(blob)>2_000_000:raise ValueError('حجم الملف يتجاوز 2 MB.')
    text=blob.decode('utf-8-sig')
    if filename.lower().endswith('.json'):return normalize_dataset(json.loads(text))
    if filename.lower().endswith('.csv'):
        rows=list(csv.DictReader(io.StringIO(text)))
        if not rows:raise ValueError('ملف CSV فارغ.')
        companies={r.get('company','XYZ Corp.') for r in rows};currencies={r.get('currency','OMR') for r in rows}
        if len(companies)!=1 or len(currencies)!=1:raise ValueError('يلزم شركة واحدة وعملة واحدة في الملف.')
        return normalize_dataset({'company':next(iter(companies)),'currency':next(iter(currencies)),'source':'CSV uploaded by user','periods':rows})
    raise ValueError('الأنواع المدعومة JSON أو CSV بترميز UTF-8.')

def to_json(data):return json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False).encode('utf-8')

def to_csv(rows):
    if not rows:return b''
    stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader()
    for row in rows:
        # Neutralize spreadsheet formula injection in exported text cells.
        safe={k:("'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v) for k,v in row.items()}
        writer.writerow(safe)
    return ('\ufeff'+stream.getvalue()).encode('utf-8')
