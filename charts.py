"""Plotly charts; tooltip values use explicit source amounts, never cumulative y."""
import plotly.graph_objects as go
PALETTE=['#7265CF','#A08ACB','#273F65','#528D95','#B48257','#397A68']
def style(fig,height=420):
    fig.update_layout(template='plotly_white',height=height,font=dict(family='Segoe UI, Tahoma, Arial',size=14,color='#293750'),paper_bgcolor='#FFFFFF',plot_bgcolor='#FFFFFF',margin=dict(l=30,r=30,t=30,b=80),colorway=PALETTE,legend=dict(orientation='h',y=-.22,x=.5,xanchor='center',font_size=12),hoverlabel=dict(bgcolor='#FFFFFF',font_family='Tahoma',font_size=14),separators='.,')
    fig.update_xaxes(showgrid=False,automargin=True,zerolinecolor='#DCE1EC')
    fig.update_yaxes(gridcolor='#EEF0F6',automargin=True,zerolinecolor='#DCE1EC')
    return fig

def bars(labels,values,percent=False,horizontal=True):
    fmt='%{text:.1%}' if percent else '%{text:,.3f}'
    if horizontal:
        fig=go.Figure(go.Bar(y=labels,x=values,orientation='h',marker_color=PALETTE[0],text=values,texttemplate=fmt,textposition='auto',hovertemplate='%{y}<br>%{x:.2%}<extra></extra>' if percent else '%{y}<br>%{x:,.3f}<extra></extra>'))
        fig.update_yaxes(autorange='reversed');fig.update_xaxes(tickformat='.0%' if percent else ',.2f',rangemode='tozero')
    else:
        fig=go.Figure(go.Bar(x=labels,y=values,marker_color=PALETTE[0],text=values,texttemplate=fmt,textposition='auto'))
        fig.update_yaxes(tickformat='.0%' if percent else ',.2f',rangemode='tozero')
    return style(fig,max(360,len(labels)*44+100))

def donut(labels,values):
    fig=go.Figure(go.Pie(labels=labels,values=values,hole=.68,marker=dict(colors=PALETTE,line=dict(color='white',width=4)),textinfo='percent',textposition='inside',sort=False,hovertemplate='%{label}<br>%{value:,.3f}<br>%{percent}<extra></extra>'))
    return style(fig,450)

def waterfall_income(d,scale=1e6,unit='مليون ر.ع'):
    labels=['الإيرادات','تكلفة المبيعات','المصروفات التشغيلية','الفائدة','الضريبة','صافي الربح']
    actual=[d['revenue'],d['cogs'],d['opex'],d['interest'],d['tax'],d['net_income']]
    changes=[actual[0],-actual[1],-actual[2],-actual[3],-actual[4],0]
    fig=go.Figure(go.Waterfall(x=labels,y=[x/scale for x in changes],customdata=[x/scale for x in actual],text=[f'{x/scale:,.3f}' for x in actual],textposition='outside',cliponaxis=False,measure=['absolute','relative','relative','relative','relative','total'],decreasing=dict(marker_color='#A08ACB'),increasing=dict(marker_color='#7265CF'),totals=dict(marker_color='#273F65'),connector=dict(line=dict(color='#D6DCE9',width=1)),hovertemplate='%{x}<br>قيمة البند: %{customdata:,.3f} '+unit+'<extra></extra>'))
    style(fig,450);fig.update_yaxes(title=unit,rangemode='tozero');fig.update_xaxes(tickangle=-20)
    return fig

def waterfall_cash(d,scale=1e6,unit='مليون ر.ع'):
    values=[d['cfo'],d['cfi'],d['cff'],d['cash_change']]
    fig=go.Figure(go.Waterfall(x=['التشغيل','الاستثمار','التمويل','صافي تغير النقد'],y=[v/scale for v in values[:3]]+[0],customdata=[v/scale for v in values],text=[f'{v/scale:+,.3f}' for v in values],textposition='outside',cliponaxis=False,measure=['relative','relative','relative','total'],increasing=dict(marker_color='#528D95'),decreasing=dict(marker_color='#B48257'),totals=dict(marker_color='#273F65'),connector=dict(line_color='#D6DCE9'),hovertemplate='%{x}<br>%{customdata:+,.3f} '+unit+'<extra></extra>'))
    style(fig,450);fig.update_yaxes(title=unit,rangemode='tozero');return fig
