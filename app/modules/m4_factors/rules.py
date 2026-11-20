from collections import Counter
from app.domain import action_math
from app.numeric import fmt
def apply(ctx):
    rows=[];factors={}
    adopted={};pending={}
    for e in ctx['eligible']:
        key=(e['event']['canonical'],e['event']['ex_date'])
        if e['status']=='已核':adopted.setdefault(key,set()).add(e['action']['record'])
        else:pending.setdefault(key,Counter())[e['action']['record']]+=1
    for event in ctx['events']:
        key=(event['canonical'],event['ex_date'])
        reference,factor=action_math(event);factors[key]={'reference':reference,'factor':factor}
        hold=pending.get(key,Counter())
        rows.append({'证券':event['canonical'],'除权日':event['ex_date'],'前收盘_CNY':event['price'],'参考价_CNY':fmt(reference),'复权因子':fmt(factor,'0.00000001'),
            '参考价采用':'+'.join(c['record'] for c in event['components']),
            '持仓采用':'+'.join(c['record'] for c in event['components'] if c['record'] in adopted.get(key,set())) or '—',
            '待核行动':'+'.join(record+'×'+str(n) for record,n in sorted(hold.items())) or '—',
            '状态':'暂定' if hold else '确认','行动版本':event['version']})
    ctx['factors']={str(k):v for k,v in factors.items()}
    return {'rows':rows,'metrics':[['参考价',len(rows),'项'],['因子',len(factors),'项'],['暂定事件',sum(r['状态']=='暂定' for r in rows),'项'],['冲突隔离',sum(r['原因码']=='CONFLICT' for r in ctx['quarantine']),'条']]}
