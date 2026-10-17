"""Local financial analysis workbench. Run: python -m streamlit run app.py"""
from pathlib import Path
from html import escape
import copy,json
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from finance import CORE,OPTIONAL,LABELS,derive,ratios,dupont,common_size,compare,simulate,budget_variances,validate_period,divide
from io_utils import normalize_dataset,load_bytes,to_json,to_csv
from charts import style,bars,donut,waterfall_income,waterfall_cash,PALETTE

ROOT=Path(__file__).resolve().parent
st.set_page_config(page_title='Financial Intelligence | XYZ',page_icon='📊',layout='wide',initial_sidebar_state='expanded')
st.markdown('<style>'+ROOT.joinpath('assets/style.css').read_text(encoding='utf-8')+'</style>',unsafe_allow_html=True)

def num(v,dec=2):return 'غير متاح' if v is None else f'{v:,.{dec}f}'
def percent(v):return 'غير متاح' if v is None else f'{v*100:,.2f}%'
def money(v):return 'غير متاح' if v is None else f'{v/SCALE:,.3f}'
def heading(t):st.markdown('<div class="fin-heading">'+escape(t)+'</div>',unsafe_allow_html=True)
def note(t):st.markdown('<div class="fin-note">'+escape(t)+'</div>',unsafe_allow_html=True)
def insight(title,body):st.markdown('<div class="fin-insight"><b>'+escape(title)+'</b><br>'+escape(body)+'</div>',unsafe_allow_html=True)
def kpis(items):
    items=[i for i in items if 'غير متاح' not in str(i[1])]
    if not items:return
    for col,(title,value,hint) in zip(st.columns(len(items)),items):
        with col:st.markdown(f'<div class="fin-card"><div class="title">{escape(title)}</div><div class="value">{escape(str(value))}</div><div class="hint">{escape(hint)}</div></div>',unsafe_allow_html=True)
def plot(fig,key):st.plotly_chart(fig,width='stretch',key=key,config={'displaylogo':False,'toImageButtonOptions':{'format':'png','scale':2}})
def table(rows,formats=None):
    df=pd.DataFrame(rows)
    if df.empty:st.info('لا توجد صفوف لهذا الاختيار.');return
    if formats:st.dataframe(df.style.format(formats,na_rep='غير متاح'),hide_index=True,width='stretch',height=min(650,45+len(df)*36))
    else:st.dataframe(df,hide_index=True,width='stretch',height=min(650,45+len(df)*36))
def csv_button(label,rows,name):st.download_button(label,to_csv(rows),file_name=name,mime='text/csv',key=name)
def fmt_ratio(r):
    if r['value'] is None:return 'غير متاح'
    if r['unit']=='percent':return percent(r['value'])
    if r['unit']=='money':return money(r['value'])+' '+UNIT
    return num(r['value'])+(' مرة' if r['unit']=='multiple' else ' يوم')

if 'dataset' not in st.session_state:
    st.session_state.dataset=normalize_dataset(json.loads(ROOT.joinpath('data/company.json').read_text(encoding='utf-8')))
data=st.session_state.dataset
with st.sidebar:
    st.markdown('<div class="fin-brand">Financial Intelligence<small>LOCAL FINANCIAL ANALYSIS</small></div>',unsafe_allow_html=True)
    page=st.radio('أقسام لوحة التحكم',['النظرة التنفيذية','القوائم وCommon Size','النسب وDuPont','التدفقات والسيولة','تغطية الفوائد','البيانات والإعدادات'],key='nav')
    st.divider()
    labels=[p['label'] for p in data['periods']]
    selected=st.selectbox('الفترة الحالية',labels,key='period_selected')
    unit=st.radio('وحدة عرض المبالغ',['مليون ر.ع','ألف ر.ع','ر.ع'],key='display_unit')
    st.caption('البيانات الأصلية والاستيراد دائماً بالريال العُماني OMR.')
    st.divider();st.download_button('تنزيل نسخة البيانات الحالية',to_json(data),file_name='financial_data.json',mime='application/json')
    st.caption('تشغيل محلي. التعديلات في الجلسة فقط حتى تنزّل البيانات وتحفظها.')
SCALE={'مليون ر.ع':1e6,'ألف ر.ع':1e3,'ر.ع':1}[unit];UNIT=unit
p=next(z for z in data['periods'] if z['label']==selected);d=derive(p);rs=[r for r in ratios(p) if r['value'] is not None and r['key'] != 'cash_conversion'];rv={z['key']:z['value'] for z in ratios(p)}
company=escape(data['company']);period=escape(selected)
st.markdown(f'<div class="fin-hero"><h1>{company} · التحليل المالي</h1><p>{period} &nbsp; / &nbsp; وحدة العرض: {escape(UNIT)} &nbsp; / &nbsp; تحليل القوائم والقرارات</p></div>',unsafe_allow_html=True)
if not p.get('period_days'):note('مدة الفترة غير محددة. العوائد ودوران الأصول تخص الفترة ولا تعرض كمعدلات سنوية.')

if page=='النظرة التنفيذية':
    kpis([('الإيرادات',money(d['revenue']),UNIT),('صافي الربح',money(d['net_income']),'هامش '+percent(rv['net_margin'])),('التدفق التشغيلي',money(d['cfo']),UNIT),('صافي التشغيل والاستثمار',money(d['cfo']+d['cfi']),UNIT+'؛ لا يساوي تلقائياً التدفق الحر')])
    c1,c2=st.columns([1.35,1],gap='large')
    with c1:heading('جسر الربحية');plot(waterfall_income(d,SCALE,UNIT),'income-bridge')
    with c2:
        heading('توزيع مصادر تمويل الأصول')
        st.caption('القيم: '+UNIT+' · النسب من إجمالي التمويل')
        if min(d['current_liabilities'],d['long_term_liabilities'],d['equity'])>=0 and d['funding']>0:plot(donut(['خصوم متداولة','خصوم طويلة الأجل','حقوق الملكية'],[d['current_liabilities']/SCALE,d['long_term_liabilities']/SCALE,d['equity']/SCALE]),'funding-pie')
        else:st.info('الملكية السالبة أو غياب إجمالي موجب يمنع عرض التركيب بدائرة. راجع جدول المركز المالي.')
    a,b=st.columns(2)
    with a:heading('هوامش الربحية');plot(bars(['مجمل الربح','التشغيل','صافي الربح'],[rv['gross_margin'] or 0,rv['operating_margin'] or 0,rv['net_margin'] or 0],percent=True),'margins') if d['revenue']!=0 else st.info('الإيرادات صفر: الهوامش غير معرّفة.')
    with b:
        heading('ما الذي تعنيه الأرقام؟')
        insight('الربح والتدفق',f"صافي الربح {num(d['net_income'],0)} ر.ع مقابل تدفق تشغيلي {num(d['cfo'],0)} ر.ع. فرق {num(d['cfo']-d['net_income'],0)} ر.ع يحتاج إلى تسوية؛ لا نفترض أنه إهلاك أو تحصيل.")
        insight('مصدر تغير النقد',f"صافي التشغيل والاستثمار {num(d['cfo']+d['cfi'],0)} ر.ع، وصافي التمويل {num(d['cff'],0)} ر.ع. زيادة النقد ليست رصيد النقد الختامي.")
        insight('الاستثمار التالي','يلزم فحص الطاقة الحالية وتدفقات المشروع قبل توظيف النقد أو زيادة الدين. لا توجد عتبات قطاعية معتمدة في المصدر.')

elif page=='القوائم وCommon Size':
    kind=st.selectbox('القائمة',['قائمة الدخل','المركز المالي','التدفقات النقدية']);statement={'قائمة الدخل':'income','المركز المالي':'balance','التدفقات النقدية':'cashflow'}[kind]
    basis='revenue'
    if statement=='cashflow':basis={'الإيرادات':'revenue','التدفق التشغيلي':'cfo'}[st.radio('أساس نسبة التدفقات',['الإيرادات','التدفق التشغيلي'],horizontal=True)]
    rows=common_size(p,statement,basis)
    heading('Common Size Analysis · التحليل بالحجم المشترك')
    den=d['revenue'] if statement=='income' else d['assets'] if statement=='balance' else d[basis]
    st.info(f"أساس النسبة: {rows[0]['denominator']} = {num(den,0)} ر.ع. النسبة = البند ÷ الأساس × 100.")
    c1,c2=st.columns([1,1.1])
    with c1:
        show=[{'البند':r['item'],'القيمة ('+UNIT+')':r['amount']/SCALE,'النسبة %':r['share']*100 if r['share'] is not None else None} for r in rows]
        table(show,{'القيمة ('+UNIT+')':'{:,.3f}','النسبة %':'{:,.2f}'})
        csv_button('تنزيل القيم والنسب CSV',rows,'common_size_'+statement+'.csv')
    with c2:
        mode=st.radio('مقياس الرسم',['النسبة','القيمة'],horizontal=True)
        if mode=='النسبة' and den==0:st.warning('الأساس صفر. النسب غير معرّفة، ولا يعوضها البرنامج بأصفار.')
        else:plot(bars([z['item'] for z in rows],[z['share'] if mode=='النسبة' else z['amount']/SCALE for z in rows],percent=mode=='النسبة'),'common-bars')
    note('المجاميع الفرعية متداخلة مع مكوناتها. لا تجمع كل نسب قائمة الدخل، ولا الأصول مع مصادر تمويلها. تغير النقد محصلة الأنشطة وليس نشاطاً إضافياً.')
    if statement=='balance':
        a,b=st.columns(2)
        with a:
            heading('تركيب الأصول')
            if d['assets']>0:plot(donut(['متداولة','ثابتة'],[d['current_assets']/SCALE,d['fixed_assets']/SCALE]),'asset-composition')
        with b:
            heading('تركيب التمويل')
            if d['equity']>=0 and d['funding']>0:plot(donut(['خصوم متداولة','خصوم طويلة الأجل','ملكية'],[d['current_liabilities']/SCALE,d['long_term_liabilities']/SCALE,d['equity']/SCALE]),'balance-funding')
    if statement=='cashflow':note('النسب موقعة: الخروج النقدي سالب. هذا أساس تحليلي معلن، ولا يمثل نسب التدفقات الداخلة فقط.')

elif page=='النسب وDuPont':
    dp=dupont(p)
    kpis([('العائد على الأصول',percent(rv['roa']),'للفترة، وفق المتوسط أو رصيد النهاية'),('العائد على الملكية',percent(rv['roe']),'للفترة، وفق المتوسط أو رصيد النهاية'),('نسبة التداول',num(rv['current_ratio']),'مرة'),('تغطية الفائدة',num(rv['interest_cover']),'مرة؛ غير معرّفة عند انعدام الفائدة')])
    heading('تفكيك العائد على حقوق الملكية · DuPont')
    st.markdown(f'<div class="fin-dupont"><strong>{percent(dp["margin"])}</strong><span>هامش الربح</span> × <strong>{num(dp["turnover"])}</strong><span>دوران الأصول</span> × <strong>{num(dp["multiplier"])}</strong><span>مضاعف الملكية</span> = <strong>{percent(dp["product"])}</strong></div>',unsafe_allow_html=True)
    note('صافي الربح/المبيعات × المبيعات/الأصول المستخدمة × الأصول المستخدمة/الملكية المستخدمة. تطبق قواعد المتوسطات نفسها في جميع الأجزاء. مضاعف أعلى لا يثبت تحسن التشغيل، وقد تتغير معه الفائدة والهامش.')
    if p.get('opening_assets') is None or p.get('opening_equity') is None:st.caption('تُستخدم أرصدة النهاية عندما تكون أرصدة البداية غير مدخلة. أدخلها في البيانات لاحتساب المتوسطات.')
    heading('DuPont الموسّع · من التشغيل إلى عائد المساهم')
    ib=divide(d['ebt'],d['ebit']);tb=divide(d['net_income'],d['ebt'])
    if ib is not None and tb is not None and dp['product'] is not None:
        factors=[('هامش التشغيل',percent(rv['operating_margin']),'EBIT / Sales'),('معامل الفوائد',percent(ib),'EBT / EBIT'),('معامل الضرائب',percent(tb),'Net income / EBT'),('دوران الأصول',num(dp['turnover'])+' ×','Sales / Assets'),('مضاعف الملكية',num(dp['multiplier'],3)+' ×','Assets / Equity')]
        cards=''.join('<div class="factor"><span>'+escape(t)+'</span><strong>'+escape(v)+'</strong><small>'+escape(f)+'</small></div>' for t,v,f in factors)
        st.markdown('<div class="factor-grid">'+cards+'</div>',unsafe_allow_html=True)
        note('حاصل ضرب العوامل الخمسة = '+percent(dp['product'])+'. معامل الفوائد والضرائب يمثل الجزء المتبقي من الربح، وليس نسبة المصروف. التفكيك علاقة حسابية ولا يثبت السببية.')
    heading('دليل المؤشرات والصيغ')
    group=st.selectbox('مجموعة المؤشرات',['الكل']+list(dict.fromkeys(z['group'] for z in rs)))
    subset=[z for z in rs if group=='الكل' or z['group']==group]
    show=[{'المجموعة':z['group'],'المؤشر':z['item'],'القيمة':fmt_ratio(z),'الصيغة':z['formula'],'الحدود / المطلوب':z['note']} for z in subset]
    table(show);csv_button('تنزيل النسب والصيغ CSV',subset,'financial_ratios.csv')
    note('تظهر فقط المؤشرات المدعومة بالمدخلات الحالية. العوائد تخص الفترة وليست بالضرورة سنوية.')

elif page=='التدفقات والسيولة':
    kpis([('تدفق التشغيل',money(d['cfo']),UNIT),('تدفق الاستثمار',money(d['cfi']),UNIT),('تدفق التمويل',money(d['cff']),UNIT),('صافي تغير النقد',money(d['cash_change']),UNIT+'، ليس رصيد النهاية')])
    c1,c2=st.columns([1.35,1],gap='large')
    with c1:heading('جسر التدفقات النقدية');plot(waterfall_cash(d,SCALE,UNIT),'cash-waterfall')
    with c2:
        heading('جودة الأرباح النقدية')
        plot(bars(['صافي الربح','تدفق التشغيل'],[d['net_income']/SCALE,d['cfo']/SCALE]),'cash-v-profit')
        note('الوحدة: '+UNIT+'. لا تكفي فترة واحدة لإثبات استدامة التحويل النقدي.')
    a,b=st.columns(2)
    with a:
        heading('المركز المتداول')
        table([{'البند':LABELS[k],'القيمة':money(d[k])+' '+UNIT} for k in ('current_assets','current_liabilities')]+[{'البند':'رأس المال العامل','القيمة':money(rv['working_capital'])+' '+UNIT}])
        cushion=divide(d['current_assets']-d['current_liabilities'],d['current_assets'])
        insight('هامش رصيد محاسبي',f"الفرق كنسبة من الأصول المتداولة {percent(cushion)}. إذا كان موجباً، فهو مقدار انخفاض الأصول حتى نسبة تداول 1 مع ثبات الخصوم؛ لا يضمن توافر نقد في موعد السداد.")
    with b:
        heading('فحوص عملية قبل القرار')
        st.write('1. توقع نقدي متجدد مع مواعيد السداد.\n2. أعمار الذمم والمخزون البطيء والنقد المقيّد.\n3. تسوية الربح بالتدفق التشغيلي.\n4. فصل أصل القروض عن الفائدة المحاسبية.\n5. تحليل الاستثمار الإجمالي بدلاً من مساواة CFI بـCapex.')
        if p.get('capex') is not None:insight('تدفق حر بعد الإنفاق الرأسمالي',money(rv['fcf'])+' '+UNIT+' = CFO − Capex. يختلف عن FCFF وقد يعتمد على تصنيف الفوائد في التدفقات.')

elif page=='تغطية الفوائد':
    heading('قدرة الأرباح التشغيلية على تغطية الفوائد')
    kpis([('تغطية الفوائد',num(rv['interest_cover'])+' ×','EBIT ÷ مصروف الفائدة'),('الربح التشغيلي',money(d['ebit']),UNIT),('مصروف الفوائد',money(d['interest']),UNIT)])
    plot(bars(['الربح التشغيلي EBIT','مصروف الفوائد'],[d['ebit']/SCALE,d['interest']/SCALE]),'interest-coverage-chart')
    note('وحدة الرسم: '+UNIT)
    insight('ماذا تقيس؟','تقارن هذه النسبة الأرباح التشغيلية بمصروف الفوائد للفترة نفسها. لا تشمل سداد أصل الدين ولا تثبت توافر النقد عند الاستحقاق.')
    insight('ما الذي نتحقق منه؟','استدامة الربح التشغيلي، توقيت التدفقات النقدية، وجدول سداد أصل الدين. لا تكفي النسبة وحدها للحكم على أمان الاستثمار.')

elif page=='البيانات والإعدادات':
    heading('إدارة بيانات محلية قابلة للمراجعة')
    st.info('التعديل والاستيراد يؤثران في الجلسة الحالية. للحفظ الدائم نزّل JSON ثم استبدل data/company.json به، أو استورده في جلسة جديدة. لا يرسل التطبيق الأرقام إلى خدمة سحابية.')
    st.caption('المصدر: '+data.get('source','User input'))
    upload=st.file_uploader('استيراد JSON أو CSV، جميع المبالغ OMR',type=['json','csv'])
    if st.button('تحميل الملف إلى الجلسة',disabled=upload is None):
        try:
            new=load_bytes(upload.getvalue(),upload.name);st.session_state.dataset=new
            st.session_state.pop('period_selected',None);st.session_state.pop('edit_values',None);st.rerun()
        except (ValueError,UnicodeError,TypeError) as e:st.error(str(e))
    st.download_button('تنزيل قالب CSV',to_csv([{'label':p['label'],**{k:p[k] for k in CORE}}]),file_name='template.csv',mime='text/csv')
    st.download_button('تنزيل ملف الحالة الأصلي JSON',ROOT.joinpath('data/company.json').read_bytes(),file_name='original_case.json',mime='application/json')
    with st.expander('قاموس الحقول وقواعد الإدخال'):
        table([{'الحقل':k,'الوصف':LABELS[k],'الحالة':'أساسي' if k in CORE else 'اختياري؛ اتركه فارغاً عند الغياب'} for k in CORE])
        st.write('المصروفات والأرصدة الموجبة تُدخل أرقاماً موجبة. CFO/CFI/CFF بإشاراتها. tax قد يكون سالباً إذا وردت منفعة ضريبية فعلية في المصدر. لا تستخدم الصفر بدلاً من مجهول. فترة label مطلوبة وفريدة. ترتيب الفترات في الملف يحدد ترتيب الاتجاه. الوحدة OMR دائماً.')
    with st.form('edit_form'):
        st.subheader('تعديل الفترة الحالية أو إضافة فترة جديدة')
        new_label=st.text_input('اسم الفترة',value=p['label'])
        period_days=st.number_input('عدد أيام الفترة (0 = غير محدد)',min_value=0,value=int(p.get('period_days') or 0),step=1)
        fields=list(CORE)
        editor=pd.DataFrame([{'field':k,'الوصف':LABELS[k],'value':float(p[k]) if p.get(k) is not None else None} for k in fields])
        edited=st.data_editor(editor,hide_index=True,width='stretch',disabled=['field','الوصف'],column_config={'value':st.column_config.NumberColumn('القيمة الأصلية بالريال OMR',format='%.4f')},height=540,key='editor_'+selected)
        add_new=st.checkbox('إضافة فترة جديدة بدلاً من تعديل الحالية')
        apply=st.form_submit_button('التحقق وتطبيق البيانات')
    if apply:
        candidate={row['field']:(None if pd.isna(row['value']) else float(row['value'])) for _,row in edited.iterrows()};candidate.update(label=new_label.strip(),period_days=period_days or None)
        errors,warnings=validate_period(candidate)
        if add_new and candidate['label'] in labels:errors.append('اختر اسم فترة جديداً غير مستخدم.')
        if not add_new and candidate['label'] in [z for z in labels if z!=selected]:errors.append('اسم الفترة مستخدم بالفعل.')
        if errors:
            for e in errors:st.error(e)
        else:
            new=copy.deepcopy(data)
            if add_new:new['periods'].append(candidate)
            else:new['periods'][labels.index(selected)]=candidate
            new['source']='بيانات أدخلها أو عدّلها المستخدم محلياً، مستندة إلى '+data.get('source','')[:200]
            st.session_state.dataset=normalize_dataset(new);st.session_state.pop('period_selected',None);st.rerun()
    heading('فحص الاتساق للمصدر الحالي')
    errors,warnings=validate_period(p)
    table([{'الفحص':'الأصول مقابل الخصوم والملكية','الطرف الأول ر.ع':d['assets'],'الطرف الثاني ر.ع':d['funding'],'الفرق ر.ع':d['assets']-d['funding']},{'الفحص':'التدفقات مقابل تغير النقد المشتق','الطرف الأول ر.ع':d['cfo']+d['cfi']+d['cff'],'الطرف الثاني ر.ع':d['cash_change'],'الفرق ر.ع':0}],{'الطرف الأول ر.ع':'{:,.2f}','الطرف الثاني ر.ع':'{:,.2f}','الفرق ر.ع':'{:,.2f}'})
    
    note('فحص التدفقات يعرض هوية جمع حسابية، وليس مطابقة مع رصيد نقد مستقل. عند إدخال cash وcash_opening يتحقق البرنامج من اتساقهما مع التدفقات. اتساق المجاميع لا يثبت تدقيق المصدر.')

st.divider();note('المصدر: '+data.get('source','')+' · حسابات الفترة المختارة. تُخفى المؤشرات التي لا تتوافر مدخلاتها. أدوات الرسم تتيح التكبير وتنزيل الصورة، والجداول تتيح البحث والفرز والتنزيل.')
