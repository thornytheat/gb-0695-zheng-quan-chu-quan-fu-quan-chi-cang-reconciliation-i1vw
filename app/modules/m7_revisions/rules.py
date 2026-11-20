from app.domain import action_math,compose,latest_snapshot,status_of,book
from app.numeric import fmt
from app.errors import DomainError
def apply(ctx):
    rows=[];by_record={}
    for event in ctx['events']:
        for component in event['components']:by_record[(event['canonical'],component['record'])]=(event,component)
    for old in ctx['action_history']:
        hit=by_record.get((old['canonical'],old['record']))
        if not hit:continue
        event,new=hit
        if old['version']==new['version']:continue
        old_components=[old if c is new else c for c in event['components']]
        try:old_event={**event,'components':old_components,**compose(old_components)}
        except DomainError:continue
        investors={}
        for item in ctx['eligible']:
            if item['event'] is not event:continue
            investors.setdefault(item['position']['record'],[]).append({'component':item['action'],'snapshot':item['position'],'status':item['status']})
        for record,entries in sorted(investors.items()):
            before=book([{'component':c,'snapshot':s,'status':status_of(s,c)} for c in old_components for s in [latest_snapshot(ctx['positions'],event['canonical'],record,c['record_date'])] if s])
            after=book(entries)
            rows.append({'证券':event['canonical'],'持仓记录':record,'旧版本':old['version'],'新版本':new['version'],'新增股份差':str(after['whole']-before['whole']),'分红差_CNY':fmt(after['cash']-before['cash'],'0.01'),'参考价差_CNY':fmt(action_math(event)[0]-action_math(old_event)[0])})
    return {'rows':rows,'metrics':[['修订影响',len(rows),'条'],['旧版留存',len(ctx['action_history']),'项'],['当前版本',max((a['version_n'] for a in ctx['actions']),default=0),'']]}
