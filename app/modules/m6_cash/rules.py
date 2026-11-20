from app.numeric import fmt
from decimal import Decimal
def apply(ctx):
    rows=[]
    for r in ctx['recon_basis']:
        expected=r['expected'];actual=r['reported'];difference=actual-expected
        rows.append({'持仓记录':r['持仓记录'],'证券':r['证券'],'应付_CNY':fmt(expected,'0.01'),'渠道报送_CNY':fmt(actual,'0.01'),'差异_CNY':fmt(difference,'0.01'),'结论':'相符' if abs(difference)<Decimal('0.005') else '差异','核态':'部分待核' if r['pending'] else '已核'})
    ctx['cash_reconciliation']=rows
    ctx['balanced']=ctx['input_count']==len(ctx['actions'])+len(ctx['action_history'])+len(ctx['positions'])+ctx['duplicates']+len(ctx['quarantine'])
    return {'rows':rows,'metrics':[['相符',sum(r['结论']=='相符' for r in rows),'条'],['差异',sum(r['结论']=='差异' for r in rows),'条'],['部分待核',sum(r['核态']=='部分待核' for r in rows),'条'],['记录守恒','相符' if ctx['balanced'] else '差异','']]}
