from decimal import Decimal,ROUND_FLOOR,ROUND_HALF_UP
from datetime import date
from app.numeric import number
from app.errors import DomainError
def day(text):
    try:return date.fromisoformat(text)
    except ValueError:raise DomainError('DATE','日期格式无效')
def action_math(a):
    price,cash,bonus,rights,rp=[number(a[k]) for k in ('price','cash','bonus','rights','rights_price')]
    if price<=0 or min(cash,bonus,rights,rp)<0:raise DomainError('ACTION','公司行动数值无效')
    reference=(price-cash+rp*rights)/(1+bonus+rights)
    if reference<=0:raise DomainError('ACTION','除权参考价不为正')
    return reference,reference/price
def compose(components):
    # One ex-date may merge several announcements (bonus/rights), each with its own record date.
    # Shared fields must agree; each ratio aspect is declared by at most one distinct non-zero value.
    def values(key):return{number(c[key]) for c in components}
    prices=values('price')
    if len(prices)!=1:raise DomainError('CONFLICT','同除权日前收盘不一致')
    merged={'price':prices.pop()}
    for key,label in (('cash','每股现金'),('bonus','送转比例'),('rights','配股比例')):
        declared={v for v in values(key) if v>0}
        if len(declared)>1:raise DomainError('CONFLICT','同除权日'+label+'不一致')
        merged[key]=declared.pop() if declared else Decimal(0)
    offered={number(c['rights_price']) for c in components if number(c['rights'])>0}
    if len(offered)>1:raise DomainError('CONFLICT','同除权日配股价不一致')
    merged['rights_price']=offered.pop() if offered else Decimal(0)
    action_math(merged)
    return merged
def latest_snapshot(positions,canonical,record,record_date):
    # Entitlement basis: the newest position snapshot on or before the component record date.
    cutoff=day(record_date);best=None
    for p in positions:
        if p['canonical']!=canonical or p['record']!=record or day(p['event_date'])>cutoff:continue
        if best is None or (p['event_date'],p['行号'])>(best['event_date'],best['行号']):best=p
    return best
def status_of(snapshot,component):
    # Registration basis is confirmed only when the snapshot is taken on the record date itself;
    # an earlier snapshot means the registration record has not arrived yet (待核).
    return '已核' if snapshot['event_date']==component['record_date'] else '待核'
def allocate_cents(amounts):
    # Aggregate cash is rounded once; rows receive cents by largest remainder.
    target=int(sum(amounts.values(),Decimal(0)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)*100)
    floors={key:int((value*100).to_integral_value(rounding=ROUND_FLOOR)) for key,value in amounts.items()}
    order=sorted(amounts,key=lambda key:(-(amounts[key]*100-floors[key]),key))
    for key in order[:target-sum(floors.values())]:floors[key]+=1
    return {key:Decimal(value)/100 for key,value in floors.items()}
def entitlement(position,action):
    shares=number(position['shares']);bonus=number(action['bonus']);rights=number(action['rights'])
    added=shares*(bonus+rights);whole=added.to_integral_value(rounding=ROUND_FLOOR)
    return {'new_shares':shares+whole,'whole':whole,'fraction':added-whole,'cash':shares*number(action['cash']),'subscription':shares*rights*number(action['rights_price'])}
def book(entries):
    # Sum entitlement parts per investor/event; pending (待核) components are withheld, never booked.
    totals={key:Decimal(0) for key in ('whole','fraction','cash','subscription','pending_whole','pending_fraction','pending_cash','pending_subscription')}
    for e in entries:
        r=entitlement(e['snapshot'],e['component'])
        if e['status']=='已核':
            totals['whole']+=r['whole'];totals['fraction']+=r['fraction'];totals['cash']+=r['cash'];totals['subscription']+=r['subscription']
        else:
            totals['pending_whole']+=r['whole'];totals['pending_fraction']+=r['fraction'];totals['pending_cash']+=r['cash'];totals['pending_subscription']+=r['subscription']
    return totals
