from sector_benchmarks import evaluate_metric

import pandas as pd
AR_CATEGORY={"Cost of Revenue":"تكلفة الإيراد","Purchases":"المشتريات","Payroll":"الرواتب والأجور","Rent":"الإيجارات","Utilities":"الخدمات والمرافق","Maintenance":"الصيانة","Fuel":"الوقود والمحروقات","Spare Parts":"قطع الغيار","Depreciation":"الإهلاك","Finance Costs":"تكاليف التمويل","Bank Charges":"رسوم وعمولات بنكية","Selling & Marketing":"البيع والتسويق","Administrative Expenses":"مصاريف إدارية وعمومية","Needs Review":"بحاجة مراجعة", "Needs Review":"بحاجة مراجعة","Admin Opex":"مصاريف إدارية وعمومية","Marketing":"التسويق","Selling Opex":"مصاريف البيع","COGS":"تكلفة الإيراد"}
def sf(x):
    try: return float(x)
    except Exception: return 0.0
def pct(x): return f"{sf(x)*100:.1f}%"
def money(x): return f"{sf(x):,.0f}"
def ar_category(cat): return AR_CATEGORY.get(str(cat), str(cat))
def explain_performance_score(pnl_model, breakeven_model=None, sector='خدمي'):
    revenue=sf(pnl_model.get('revenue',0)); gross=sf(pnl_model.get('gross_profit',0)); net=sf(pnl_model.get('net_profit',0)); cogs=sf(pnl_model.get('cogs',0)); opex=sf(pnl_model.get('opex',0)); mos=sf((breakeven_model or {}).get('margin_of_safety',0))
    gm=gross/revenue if revenue else 0; nm=net/revenue if revenue else 0; orat=opex/revenue if revenue else 0; dcr=cogs/revenue if revenue else 0
    rows=pd.DataFrame([
        ['هامش مجمل الربح',pct(gm),'40% فأكثر','يقيس قدرة الإيرادات على تغطية تكلفة الإيراد المباشرة.','جيد' if gm>=.4 else 'يحتاج مراجعة'],
        ['هامش صافي الربح',pct(nm),'10% فأكثر','يقيس ما يبقى فعلياً من كل وحدة إيراد بعد كل التكاليف.','جيد' if nm>=.1 else 'خطر'],
        ['نسبة المصاريف التشغيلية',pct(orat),'45% كحد مراقبة','توضح عبء المصاريف الإدارية والتشغيلية على الإيرادات.','مراقبة' if orat>.45 else 'مقبول'],
        ['نسبة تكلفة الإيراد',pct(dcr),'50% كحد مراقبة','ترتبط بالمشتريات وتكلفة تقديم الخدمة أو البضاعة.','مقبول' if dcr<=.5 else 'مرتفع'],
        ['هامش الأمان من التعادل',pct(mos),'20% فأكثر','يقيس المسافة المتاحة قبل أن تصل الإيرادات إلى نقطة التعادل.','جيد' if mos>=.2 else 'محدود'],
    ], columns=['العامل','القيمة','الحد المرجعي','كيف يؤثر؟','التقييم'])
    score=(25 if gm>=.4 else 10)+(25 if nm>=.1 else 8)+(20 if orat<=.45 else 8)+(15 if dcr<=.5 else 6)+(15 if mos>=.2 else 5)
    if orat>.45: rec='الأولوية الحالية: ضبط المصاريف التشغيلية قبل أي التزام جديد.'
    elif dcr>.5: rec='الأولوية الحالية: مراجعة تكلفة الإيراد والمشتريات والتسعير.'
    elif mos<.2: rec='الأولوية الحالية: رفع هامش الأمان عبر زيادة الإيراد أو خفض التكاليف الثابتة.'
    else: rec='الأولوية الحالية: تثبيت الانضباط الداخلي ومراقبة الهوامش شهرياً.'
    return {'score':min(100,round(score)),'recommendation':rec,'rows':rows,'note':'هذا المؤشر لا يقيس السيولة أو التحصيل أو الديون بعد؛ لذلك هو مؤشر أداء وربحية وليس حكماً كاملاً على الصحة المالية.'}
def explain_break_even(breakeven_model, mapping_df=None):
    revenue=sf((breakeven_model or {}).get('revenue',0)); be=sf((breakeven_model or {}).get('break_even_revenue',(breakeven_model or {}).get('breakeven_revenue',0))); gap=sf((breakeven_model or {}).get('breakeven_gap', revenue-be)); mos=sf((breakeven_model or {}).get('margin_of_safety',0)); fixed=sf((breakeven_model or {}).get('fixed_costs',0)); cm=sf((breakeven_model or {}).get('contribution_margin',0))
    meaning=f'الإيرادات الحالية أعلى من نقطة التعادل بمبلغ {money(gap)}؛ أي يمكن أن تنخفض الإيرادات تقريباً {pct(mos)} قبل الاقتراب من الخسارة.' if be else 'لا يمكن الاعتماد على نقطة التعادل قبل اكتمال تصنيف التكاليف.'
    score=70; reasons=['يعتمد الحساب على قائمة الدخل الرسمية.']
    if mapping_df is not None and not getattr(mapping_df,'empty',True):
        if 'classification_confidence' in mapping_df.columns:
            low=(pd.to_numeric(mapping_df['classification_confidence'], errors='coerce').fillna(100)<70).mean()
            if low>.25: score-=15; reasons.append('توجد نسبة ملحوظة من الحسابات ذات ثقة تصنيف منخفضة.')
            else: score+=10; reasons.append('معظم التصنيفات ذات ثقة مقبولة.')
        if 'user_category' in mapping_df.columns:
            other=mapping_df['user_category'].astype(str).str.contains('Other',case=False,na=False).mean()
            if other>.25: score-=15; reasons.append('نسبة البنود المصنفة كبنود بحاجة مراجعة ما زالت مرتفعة.')
            else: score+=5; reasons.append('نسبة المصاريف غير المحددة ضمن مستوى مقبول.')
    else:
        score-=20; reasons.append('لم يتم العثور على جدول تصنيف مصاريف معتمد.')
    score=max(0,min(100,score)); label='عالية' if score>=80 else ('متوسطة' if score>=60 else 'منخفضة')
    rows=pd.DataFrame([['التكاليف الثابتة',money(fixed),'مصاريف لا تتغير مباشرة مع حجم المبيعات.'],['هامش المساهمة',pct(cm),'النسبة المتبقية من الإيراد بعد التكاليف المتغيرة لتغطية الثابت والربح.'],['إيراد التعادل',money(be),'المبيعات المطلوبة لتغطية التكاليف دون ربح أو خسارة.'],['فجوة التعادل',money(gap),'المسافة الحالية بين الإيرادات الفعلية وإيراد التعادل.'],['هامش الأمان',pct(mos),'نسبة الانخفاض الممكنة في الإيراد قبل الوصول للتعادل.']], columns=['المؤشر','القيمة','ماذا يعني لرب العمل؟'])
    return {'meaning':meaning,'confidence_label':label,'confidence_score':score,'confidence_reasons':reasons,'formula_rows':rows}
def build_sensitivity_explanations(df):
    if df is None or df.empty: return df
    out=df.copy(); exp=[]; act=[]
    for _,r in out.iterrows():
        sc=str(r.get('السيناريو','')); gap=sf(r.get('فجوة التعادل',0))
        if gap<=0: exp.append('السيناريو يضع النشاط عند أو تحت نقطة التعادل.'); act.append('خفض التكاليف الثابتة أو رفع هامش المساهمة فوراً.')
        elif 'ارتفاع التكاليف' in sc and 'انخفاض' in sc: exp.append('أسوأ حالة: ارتفاع التكاليف مع تراجع الهامش يرفع نقطة التعادل.'); act.append('عدم إضافة التزامات ثابتة جديدة قبل ضبط التكلفة.')
        elif 'ارتفاع التكاليف' in sc: exp.append('يوضح أثر زيادة الرواتب أو الإيجارات أو الالتزامات الثابتة.'); act.append('ربط أي زيادة ثابتة بنمو مؤكد في الإيراد.')
        elif 'انخفاض هامش' in sc: exp.append('يوضح أثر تراجع التسعير أو ارتفاع تكلفة الإيراد.'); act.append('مراجعة التسعير والمشتريات وتكلفة الخدمة.')
        elif 'تحسين' in sc: exp.append('يوضح أثر تخفيض التكاليف أو تحسين الهامش.'); act.append('تحديد بنود كفاءة قابلة للتنفيذ.')
        else: exp.append('الوضع المرجعي الحالي للحساب.'); act.append('استخدامه كخط أساس للمقارنة.')
    out['ماذا يعني؟']=exp; out['الإجراء']=act; return out
def build_expense_quality(expense_model, pnl_model):
    revenue=sf((pnl_model or {}).get('revenue',0))
    if not expense_model or expense_model.get('by_category',pd.DataFrame()).empty:
        return {'summary':pd.DataFrame(),'diagnosis':'لا توجد بيانات كافية للمصاريف.','action':'رفع ملف مصاريف وتصنيف البنود.'}
    df=expense_model['by_category'].copy(); df['amount']=pd.to_numeric(df['amount'], errors='coerce').fillna(0); df['التصنيف']=df['category'].apply(ar_category); df['النسبة من الإيراد']=df['amount']/revenue if revenue else 0; df['التقييم']=df['النسبة من الإيراد'].apply(lambda x:'مرتفع' if x>.2 else ('متوسط' if x>.1 else 'مقبول')); df=df.rename(columns={'amount':'المبلغ'})
    max_row=df.sort_values('المبلغ',ascending=False).iloc[0]; other=df[df['التصنيف'].astype(str).str.contains('أخرى',na=False)]['المبلغ'].sum(); other_ratio=other/revenue if revenue else 0
    if other_ratio>.1: diagnosis=f'يوجد بند بنود بحاجة مراجعة بقيمة {money(other)}، وهذا يقلل وضوح قرارات خفض التكاليف.'; action='تفصيل المصاريف الأخرى قبل أي قرار خفض أو إعادة تسعير.'
    else: diagnosis=f'أكبر بند مصاريف هو {max_row["التصنيف"]} بقيمة {money(max_row["المبلغ"])}.'; action='مراجعة أكبر بندين وربطهما بالإيراد قبل اعتماد أي التزامات جديدة.'
    return {'summary':df[['التصنيف','المبلغ','النسبة من الإيراد','التقييم']],'diagnosis':diagnosis,'action':action}
