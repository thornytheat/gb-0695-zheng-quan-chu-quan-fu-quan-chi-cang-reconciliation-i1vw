from app.domain import latest_snapshot,status_of

def apply(ctx):
    rows=[];eligible=[];selected=set()
    investors={}
    for p in ctx['positions']:investors.setdefault(p['canonical'],set()).add(p['record'])
    for event in ctx['events']:
        for component in event['components']:
            for record in sorted(investors.get(event['canonical'],())):
                snapshot=latest_snapshot(ctx['positions'],event['canonical'],record,component['record_date'])
                if snapshot is None:continue
                status=status_of(snapshot,component)
                eligible.append({'position':snapshot,'action':component,'event':event,'status':status})
                selected.add((snapshot['record'],snapshot['event_date']))
                rows.append({'持仓记录':snapshot['record'],'证券':snapshot['canonical'],'资格':'有登记权益','核态':status,'股份':snapshot['shares'],'行动':component['record'],'登记日':component['record_date'],'采用快照':snapshot['event_date']})
    for p in ctx['positions']:
        if (p['record'],p['event_date']) not in selected:
            rows.append({'持仓记录':p['record'],'证券':p['canonical'],'资格':'无登记权益','核态':'—','股份':p['shares'],'行动':'','登记日':'','采用快照':''})
    ctx['eligible']=eligible
    pending=sum(e['status']=='待核' for e in eligible)
    return {'rows':rows,'metrics':[['有权益',len(eligible),'条'],['无权益',sum(r['资格']=='无登记权益' for r in rows),'条'],['登记日',' / '.join(sorted({a['record_date'] for a in ctx['actions']})),''],['待核权益',pending,'条']]}
