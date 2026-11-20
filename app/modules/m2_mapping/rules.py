from app.domain import action_math,day,compose
from app.numeric import number
from app.errors import DomainError
from app.reasons import isolate
def apply(ctx):
    positions=[];groups={};seen=set();duplicates=0
    for r in ctx['rows']:
        try:
            if not r['record'] or not r['security']:raise DomainError('MISSING','证券或记录编号为空')
            if r['kind'] not in ('action','position'):raise DomainError('KIND','业务类别无效')
            security=r['alias'] or r['security'];item={**r,'canonical':security}
            day(r['event_date'])
            key=tuple((k,v) for k,v in r.items() if k!='行号')
            if key in seen:duplicates+=1;continue
            seen.add(key)
            if r['kind']=='action':
                action_math(r);record,ex=day(r['record_date']),day(r['ex_date'])
                if record>=ex:raise DomainError('DATE_ORDER','登记日必须早于除权日')
                version=int(r['version'])
                if version<1:raise ValueError()
                item['version_n']=version;groups.setdefault((security,r['record']),[]).append(item)
            else:
                shares=number(r['shares']);number(r['reported_cash'])
                if shares<0 or shares!=shares.to_integral_value():raise DomainError('SHARES','持仓须为非负整数')
                positions.append(item)
        except DomainError as e:isolate(ctx,r,e.code,e.message)
        except ValueError:isolate(ctx,r,'VERSION','版本必须为正整数')
    # Revisions of one announcement share its record id: highest version wins, ties must agree.
    winners=[];history=[]
    for key,items in sorted(groups.items()):
        version=max(r['version_n'] for r in items);top=[r for r in items if r['version_n']==version]
        signatures={tuple(r[k] for k in ('price','cash','bonus','rights','rights_price','record_date','ex_date')) for r in top}
        if len(signatures)>1:
            for r in items:isolate(ctx,r,'CONFLICT','同版本公司行动定义冲突')
            continue
        winner=min(top,key=lambda r:r['行号']);winners.append(winner)
        history.extend(r for r in items if r is not winner)
    # Announcements with distinct record ids sharing one ex-date compose a single ex-rights event.
    events=[];actions=[];by_event={}
    for w in winners:by_event.setdefault((w['canonical'],w['ex_date']),[]).append(w)
    for key,components in sorted(by_event.items()):
        components=sorted(components,key=lambda r:r['record'])
        try:merged=compose(components)
        except DomainError as e:
            for r in components:isolate(ctx,r,e.code,e.message)
            continue
        event={'canonical':key[0],'ex_date':key[1],'components':components,'record_dates':sorted({c['record_date'] for c in components}),'record':'+'.join(c['record'] for c in components),'version':'+'.join(c['version'] for c in components),'version_n':max(c['version_n'] for c in components),**merged}
        events.append(event);actions.extend(components)
    # Snapshot positions must be unique per investor/stock/date.
    unique={};valid=[]
    for r in positions:
        key=(r['record'],r['canonical'],r['event_date'])
        if key in unique:isolate(ctx,r,'POSITION_CONFLICT','同日持仓记录冲突');continue
        unique[key]=r;valid.append(r)
    ctx.update(actions=actions,events=events,action_history=history,positions=valid,duplicates=duplicates)
    rows=[{'记录':r['record'],'类别':r['kind'],'证券':r['canonical'],'版本':r['version'],'行号':r['行号']} for r in actions+valid]
    return {'rows':rows,'metrics':[['有效行动',len(actions),'项'],['除权事件',len(events),'项'],['持仓',len(valid),'条'],['旧版行动',len(history),'项'],['重复行',duplicates,'条']]}
