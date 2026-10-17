"""Financial calculations in OMR. No UI or network dependencies."""
from math import isfinite

CORE = ('revenue','cogs','opex','interest','tax','current_assets','fixed_assets','current_liabilities','long_term_liabilities','equity','cfo','cfi','cff')
OPTIONAL = ('opening_assets','opening_equity','inventory','receivables','payables','prepayments','cash','cash_opening','depreciation','capex','interest_bearing_debt','debt_principal_paid','cash_interest_paid','cash_tax_paid','opening_inventory','opening_receivables','opening_payables','credit_sales','credit_purchases','period_days','operating_current_assets','operating_current_liabilities','invested_capital','tax_rate_assumption','budget_revenue','budget_cogs','budget_opex')
LABELS = {'revenue':'الإيرادات','cogs':'تكلفة المبيعات','gross_profit':'مجمل الربح','opex':'المصروفات التشغيلية','ebit':'الربح التشغيلي EBIT','interest':'مصروف الفائدة','ebt':'الربح قبل الضريبة','tax':'مصروف الضريبة','net_income':'صافي الربح','current_assets':'الأصول المتداولة','fixed_assets':'الأصول الثابتة','assets':'إجمالي الأصول','current_liabilities':'الخصوم المتداولة','long_term_liabilities':'الخصوم طويلة الأجل','liabilities':'إجمالي الخصوم','equity':'حقوق الملكية','funding':'إجمالي الخصوم وحقوق الملكية','cfo':'تدفق التشغيل','cfi':'تدفق الاستثمار','cff':'تدفق التمويل','cash_change':'صافي تغير النقد','opening_assets':'أصول أول الفترة','opening_equity':'حقوق ملكية أول الفترة','inventory':'المخزون','receivables':'الذمم المدينة','payables':'الذمم الدائنة','prepayments':'المصروفات المقدمة','cash':'نقد آخر الفترة','cash_opening':'نقد أول الفترة','depreciation':'الإهلاك والإطفاء','capex':'الإنفاق الرأسمالي النقدي','interest_bearing_debt':'الدين المالي بفائدة','debt_principal_paid':'أصل القرض المدفوع','cash_interest_paid':'الفائدة المدفوعة نقداً','cash_tax_paid':'الضريبة المدفوعة نقداً','period_days':'مدة الفترة بالأيام','opening_inventory':'مخزون أول الفترة','opening_receivables':'ذمم مدينة أول الفترة','opening_payables':'ذمم دائنة أول الفترة','credit_sales':'المبيعات الآجلة','credit_purchases':'المشتريات الآجلة','operating_current_assets':'أصول متداولة تشغيلية','operating_current_liabilities':'خصوم متداولة تشغيلية','invested_capital':'متوسط رأس المال المستثمر التشغيلي','tax_rate_assumption':'معدل ضريبة افتراضي (0–1)','budget_revenue':'إيرادات الموازنة','budget_cogs':'تكلفة مبيعات الموازنة','budget_opex':'تشغيل الموازنة'}
INCOME = ('revenue','cogs','gross_profit','opex','ebit','interest','ebt','tax','net_income')
BALANCE = ('current_assets','fixed_assets','assets','current_liabilities','long_term_liabilities','liabilities','equity','funding')
CASHFLOW = ('cfo','cfi','cff','cash_change')

def divide(a,b):
    if a is None or b is None or b == 0: return None
    return a/b

def derive(p):
    d=dict(p)
    d['gross_profit']=d['revenue']-d['cogs']; d['ebit']=d['gross_profit']-d['opex']
    d['ebt']=d['ebit']-d['interest']; d['net_income']=d['ebt']-d['tax']
    d['assets']=d['current_assets']+d['fixed_assets'];d['liabilities']=d['current_liabilities']+d['long_term_liabilities']
    d['funding']=d['liabilities']+d['equity'];d['cash_change']=d['cfo']+d['cfi']+d['cff']
    return d

def validate_period(p):
    errors=[];warnings=[]
    if not isinstance(p,dict): return ['الفترة يجب أن تكون كائناً JSON.'],[]
    if not str(p.get('label','')).strip():errors.append('اسم الفترة label مطلوب.')
    for k in CORE:
        v=p.get(k)
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not isfinite(v):errors.append(f'قيمة رقمية محدودة مطلوبة: {k}')
        elif k not in ('tax','cfo','cfi','cff','equity') and v<0:errors.append(f'{k}: يجب إدخال مبلغ غير سالب؛ مصروفات الدخل تُدخل موجبة.')
    for k in OPTIONAL:
        v=p.get(k)
        if v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not isfinite(v)):errors.append(f'{k}: قيمة اختيارية غير صالحة.')
        elif v is not None and k!='opening_equity' and v<0:errors.append(f'{k}: القيمة الاختيارية يجب ألا تكون سالبة.')
    if errors:return errors,warnings
    if p.get('period_days') is not None and p['period_days']<=0:errors.append('مدة الفترة يجب أن تكون موجبة.')
    if p.get('tax_rate_assumption') is not None and not 0<=p['tax_rate_assumption']<=1:errors.append('معدل الضريبة الافتراضي بين 0 و1.')
    d=derive(p)
    if abs(d['assets']-d['funding'])>0.01:errors.append(f"المركز المالي غير متوازن: الفرق {d['assets']-d['funding']:,.2f} ر.ع.")
    for k in ('cash','inventory','receivables','prepayments'):
        if p.get(k) is not None and p[k]>p['current_assets']+.01:errors.append(f'{LABELS[k]} يتجاوز الأصول المتداولة.')
    parts=[p.get(k) for k in ('cash','inventory','receivables','prepayments')]
    if sum(v for v in parts if v is not None)>p['current_assets']+.01:errors.append('مجموع مكونات الأصول المتداولة المدخلة يتجاوز إجماليها.')
    if p.get('payables') is not None and p['payables']>p['current_liabilities']+.01:errors.append('الذمم الدائنة تتجاوز الخصوم المتداولة.')
    if p.get('cash') is not None and p.get('cash_opening') is not None and abs(p['cash']-p['cash_opening']-d['cash_change'])>.01:errors.append('نقد آخر الفترة لا يطابق نقد أول الفترة + صافي التدفقات.')
    if p.get('credit_sales') is not None and p['credit_sales']>p['revenue']+.01:errors.append('المبيعات الآجلة تتجاوز إجمالي الإيرادات.')
    if not p.get('period_days'):warnings.append('مدة الفترة غير معروفة: العوائد ودوران الأصول للفترة دون تحويل سنوي، ولا حساب لأيام الدورة النقدية.')
    if p.get('opening_assets') is None or p.get('opening_equity') is None:warnings.append('عوائد الأصول والملكية تستخدم رصيد النهاية عند غياب أرصدة البداية.')
    if p.get('capex') is None:warnings.append('صافي الاستثمار ليس Capex. لا يمكن حساب التدفق النقدي الحر بهذه البيانات.')
    return errors,warnings

def common_size(p,statement='income',cash_basis='revenue'):
    d=derive(p)
    if statement=='income':fields=INCOME;den=d['revenue'];den_label='الإيرادات'
    elif statement=='balance':fields=BALANCE;den=d['assets'];den_label='إجمالي الأصول'
    elif statement=='cashflow':fields=CASHFLOW;den=d[cash_basis];den_label=LABELS[cash_basis]
    else:raise ValueError('Unknown statement')
    return [{'key':k,'item':LABELS[k],'amount':d[k],'share':divide(d[k],den),'denominator':den_label} for k in fields]

def average_or_end(p,opening,closing):return (p[opening]+closing)/2 if p.get(opening) is not None else closing

def ratios(p):
    d=derive(p);aa=average_or_end(p,'opening_assets',d['assets']);ae=average_or_end(p,'opening_equity',d['equity'])
    rows=[]
    def add(group,key,title,value,unit,formula,note=''):
        rows.append(dict(group=group,key=key,item=title,value=value,unit=unit,formula=formula,note=note))
    add('الربحية','gross_margin','هامش مجمل الربح',divide(d['gross_profit'],d['revenue']),'percent','مجمل الربح ÷ الإيرادات')
    add('الربحية','operating_margin','هامش التشغيل',divide(d['ebit'],d['revenue']),'percent','EBIT ÷ الإيرادات')
    add('الربحية','net_margin','هامش صافي الربح',divide(d['net_income'],d['revenue']),'percent','صافي الربح ÷ الإيرادات')
    add('الربحية','tax_rate','الضريبة الفعلية',divide(d['tax'],d['ebt']) if d['ebt']>0 else None,'percent','الضريبة ÷ الربح قبل الضريبة','لا يمثل معدل الضريبة القانوني؛ غير معروض عندما EBT غير موجب.')
    add('السيولة','current_ratio','نسبة التداول',divide(d['current_assets'],d['current_liabilities']),'multiple','الأصول المتداولة ÷ الخصوم المتداولة')
    quick=divide(d['current_assets']-p['inventory']-p['prepayments'],d['current_liabilities']) if p.get('inventory') is not None and p.get('prepayments') is not None else None
    add('السيولة','quick_ratio','النسبة السريعة',quick,'multiple','(الأصول المتداولة − المخزون − المقدمات) ÷ الخصوم المتداولة','تتطلب المخزون والمصروفات المقدمة؛ بقية الأصول يجب أن تكون سريعة التحول إلى نقد.')
    add('السيولة','cash_ratio','النسبة النقدية',divide(p.get('cash'),d['current_liabilities']),'multiple','النقد وما يعادله غير المقيّد ÷ الخصوم المتداولة','يلزم إدخال النقد غير المقيّد.')
    add('السيولة','working_capital','رأس المال العامل',d['current_assets']-d['current_liabilities'],'money','الأصول المتداولة − الخصوم المتداولة')
    add('التمويل','liability_assets','الخصوم إلى الأصول',divide(d['liabilities'],d['assets']),'percent','إجمالي الخصوم ÷ الأصول','ليست نسبة الدين المالي.')
    add('التمويل','liability_equity','الخصوم إلى الملكية',divide(d['liabilities'],d['equity']) if d['equity']>0 else None,'multiple','إجمالي الخصوم ÷ حقوق الملكية','غير ذي دلالة عند ملكية غير موجبة.')
    add('التمويل','debt_equity','الدين المالي إلى الملكية',divide(p.get('interest_bearing_debt'),d['equity']) if d['equity']>0 else None,'multiple','الدين بفائدة ÷ حقوق الملكية','لا يُستعاض عن الدين المالي بإجمالي الخصوم.')
    add('التمويل','interest_cover','تغطية الفائدة',divide(d['ebit'],d['interest']),'multiple','EBIT ÷ مصروف الفائدة','غياب الفائدة لا يعرض كنسبة صفر.')
    note_a='متوسط الأصول' if p.get('opening_assets') is not None else 'رصيد الأصول في نهاية الفترة كبديل معلن'
    note_e='متوسط الملكية' if p.get('opening_equity') is not None else 'رصيد حقوق الملكية في نهاية الفترة كبديل معلن'
    add('العوائد والكفاءة','roa','العائد على الأصول',divide(d['net_income'],aa) if aa>0 else None,'percent','صافي الربح ÷ الأصول المستخدمة',note_a+'؛ عائد الفترة.')
    add('العوائد والكفاءة','roe','العائد على حقوق الملكية',divide(d['net_income'],ae) if ae>0 else None,'percent','صافي الربح ÷ حقوق الملكية المستخدمة',note_e+'؛ عائد الفترة.')
    add('العوائد والكفاءة','asset_turnover','دوران الأصول',divide(d['revenue'],aa) if aa>0 else None,'multiple','الإيرادات ÷ الأصول المستخدمة',note_a)
    add('العوائد والكفاءة','equity_multiplier','مضاعف حقوق الملكية',divide(aa,ae) if aa>0 and ae>0 else None,'multiple','الأصول المستخدمة ÷ الملكية المستخدمة','نفس قواعد المتوسطات المستخدمة في DuPont.')
    add('التدفقات','cash_conversion','التدفق التشغيلي إلى الربح',divide(d['cfo'],d['net_income']) if d['net_income']>0 else None,'multiple','CFO ÷ صافي الربح','غير ذي دلالة عندما صافي الربح غير موجب.')
    add('التدفقات','cfo_margin','هامش التدفق التشغيلي',divide(d['cfo'],d['revenue']),'percent','CFO ÷ الإيرادات')
    add('التدفقات','cfo_cl','التشغيل إلى الخصوم المتداولة',divide(d['cfo'],d['current_liabilities']),'multiple','CFO ÷ خصوم نهاية الفترة','تدفق فترة مقابل رصيد نهاية؛ لا يثبت توقيت السداد.')
    add('التدفقات','after_investing','صافي التشغيل والاستثمار',d['cfo']+d['cfi'],'money','CFO + CFI','لا يسمى FCF دون تفاصيل الاستثمار.')
    add('التدفقات','fcf','التدفق الحر بعد Capex',d['cfo']-p['capex'] if p.get('capex') is not None else None,'money','CFO − Capex النقدي','تقريب معلن للتدفق الحر بعد الإنفاق الرأسمالي، وليس FCFF.')
    ebitda=d['ebit']+p['depreciation'] if p.get('depreciation') is not None else None
    add('الربحية','ebitda','EBITDA',ebitda,'money','EBIT + الإهلاك والإطفاء','يلزم أن يكون الإهلاك والإطفاء ضمن تكلفة المبيعات أو التشغيل.')
    days=p.get('period_days');ai=average_or_end(p,'opening_inventory',p.get('inventory')) if p.get('inventory') is not None else None
    ar=average_or_end(p,'opening_receivables',p.get('receivables')) if p.get('receivables') is not None else None
    ap=average_or_end(p,'opening_payables',p.get('payables')) if p.get('payables') is not None else None
    dio=divide(ai*days,d['cogs']) if ai is not None and days else None
    dso=divide(ar*days,p.get('credit_sales')) if ar is not None and days else None
    dpo=divide(ap*days,p.get('credit_purchases')) if ap is not None and days else None
    add('الدورة النقدية','dio','أيام المخزون DIO',dio,'days','متوسط المخزون ÷ COGS × أيام الفترة','رصيد نهاية بديل إذا غاب رصيد البداية.')
    add('الدورة النقدية','dso','أيام التحصيل DSO',dso,'days','متوسط الذمم المدينة ÷ المبيعات الآجلة × الأيام','لا يفترض أن كل المبيعات آجلة.')
    add('الدورة النقدية','dpo','أيام السداد DPO',dpo,'days','متوسط الذمم الدائنة ÷ المشتريات الآجلة × الأيام','لا يستعاض عن المشتريات بتكلفة المبيعات تلقائياً.')
    add('الدورة النقدية','ccc','دورة تحويل النقد CCC',dio+dso-dpo if all(x is not None for x in (dio,dso,dpo)) else None,'days','DIO + DSO − DPO')
    add('العوائد والكفاءة','fixed_turnover','دوران الأصول الثابتة',divide(d['revenue'],d['fixed_assets']) if d['fixed_assets']>0 else None,'multiple','الإيرادات ÷ الأصول الثابتة الختامية','يستخدم رصيد نهاية الفترة.')
    wc=d['current_assets']-d['current_liabilities']
    add('العوائد والكفاءة','wc_turnover','دوران رأس المال العامل',divide(d['revenue'],wc) if wc>0 else None,'multiple','الإيرادات ÷ رأس المال العامل الختامي','ارتفاع النسبة وحده لا يثبت الكفاءة.')
    add('التمويل','equity_assets','حقوق الملكية إلى الأصول',divide(d['equity'],d['assets']),'percent','حقوق الملكية ÷ الأصول')
    return rows

def dupont(p):
    rs={r['key']:r['value'] for r in ratios(p)}
    parts=[rs[k] for k in ('net_margin','asset_turnover','equity_multiplier')]
    product=parts[0]*parts[1]*parts[2] if all(v is not None for v in parts) else None
    return dict(margin=parts[0],turnover=parts[1],multiplier=parts[2],roe=rs['roe'],product=product)

def compare(current,previous,statement='income'):
    a,b=derive(current),derive(previous);fields={'income':INCOME,'balance':BALANCE,'cashflow':CASHFLOW}[statement]
    return [dict(key=k,item=LABELS[k],current=a[k],previous=b[k],change=a[k]-b[k],change_pct=(a[k]-b[k])/b[k] if b[k]>0 else None) for k in fields]

def simulate(p,volume=0,price=0,cost=0,opex=0,interest=0,variable_share=100,tax_rate=.25):
    for v in (volume,price,cost,opex,interest):
        if v < -100:raise ValueError('Changes cannot be below -100%.')
    if not 0<=variable_share<=100 or not 0<=tax_rate<=1:raise ValueError('Invalid assumption.')
    v=1+volume/100;pr=1+price/100;uc=1+cost/100;vs=variable_share/100
    r=p['revenue']*v*pr;c=p['cogs']*(vs*v*uc+1-vs);o=p['opex']*(1+opex/100);i=p['interest']*(1+interest/100)
    ebit=r-c-o;ebt=ebit-i;t=max(0,ebt)*tax_rate;ni=ebt-t
    contribution=1-divide(p['cogs']*vs*uc,p['revenue']*pr) if p['revenue']*pr else None
    fixed=p['cogs']*(1-vs)+o
    op_break=divide(fixed,contribution) if contribution is not None and contribution>0 else None
    pt_break=divide(fixed+i,contribution) if contribution is not None and contribution>0 else None
    return dict(revenue=r,cogs=c,gross_profit=r-c,opex=o,interest=i,ebit=ebit,ebt=ebt,tax=t,net_income=ni,margin=divide(ni,r),interest_cover=divide(ebit,i),contribution=contribution,operating_break_even=op_break,pretax_break_even=pt_break,safety=1-pt_break/r if pt_break is not None and r else None)

def budget_variances(p):
    fields=('budget_revenue','budget_cogs','budget_opex')
    if any(p.get(k) is None for k in fields):return None
    d=derive(p);out=[]
    for k,bk in zip(('revenue','cogs','opex'),fields):
        delta=d[k]-p[bk];good=delta>0 if k=='revenue' else delta<0
        out.append(dict(item=LABELS[k],actual=d[k],budget=p[bk],delta=delta,variance_pct=divide(delta,p[bk]),assessment='متعادل' if abs(delta)<.01 else 'ملائم حسابياً' if good else 'غير ملائم حسابياً'))
    be=p['budget_revenue']-p['budget_cogs']-p['budget_opex'];de=d['ebit']-be
    out.append(dict(item='EBIT',actual=d['ebit'],budget=be,delta=de,variance_pct=divide(de,be) if be>0 else None,assessment='متعادل' if abs(de)<.01 else 'ملائم حسابياً' if de>0 else 'غير ملائم حسابياً'))
    return out
