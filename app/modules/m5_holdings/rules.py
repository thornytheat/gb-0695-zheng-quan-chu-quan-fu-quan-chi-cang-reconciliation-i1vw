from app.domain import allocate_cents,book
from app.numeric import number,fmt
from decimal import Decimal
def apply(ctx):
    groups={};rows=[];recon=[]
    for item in ctx['eligible']:groups.setdefault((item['event']['canonical'],item['event']['ex_date']),[]).append(item)
    for key,items in sorted(groups.items()):
        by_investor={}
        for item in items:by_investor.setdefault(item['position']['record'],[]).append(item)
        books={record:book([{'component':i['action'],'snapshot':i['position'],'status':i['status']} for i in entries]) for record,entries in by_investor.items()}
        cash=allocate_cents({record:b['cash'] for record,b in books.items()})
        for record in sorted(by_investor):
            entries=by_investor[record];b=books[record]
            base=max((e['position'] for e in entries),key=lambda p:(p['event_date'],p['行号']))
            confirmed=[e for e in entries if e['status']=='已核'];pending=[e for e in entries if e['status']=='待核']
            snapshots={e['position']['行号']:e['position'] for e in entries}
            rows.append({'持仓记录':record,'证券':key[0],'快照日':base['event_date'],'除权日':key[1],'原股份':base['shares'],
                '新股份':str(number(base['shares'])+b['whole']),'零碎股':str(b['fraction']),'待核股份':str(b['pending_whole']),
                '分红_CNY':fmt(cash[record],'0.01'),'认配支付_CNY':fmt(b['subscription'],'0.01'),'待核认配_CNY':fmt(b['pending_subscription'],'0.01'),
                '采用行动':'+'.join(e['action']['record']+'@'+e['position']['event_date'] for e in confirmed) or '—',
                '待核行动':'+'.join(e['action']['record']+'（缺'+e['action']['record_date']+'登记）' for e in pending) or '—',
                '状态':'部分待核' if pending else '已核','行动版本':entries[0]['event']['version'],'行号':base['行号']})
            recon.append({'持仓记录':record,'证券':key[0],'expected':cash[record],'pending':bool(pending),
                'reported':sum((number(p['reported_cash']) for p in snapshots.values()),Decimal(0))})
    ctx['holdings']=rows;ctx['recon_basis']=recon
    return {'rows':rows,'metrics':[['重算持仓',len(rows),'条'],['零碎股记录',sum(r['零碎股']!='0' for r in rows),'条'],['待核股份',str(sum((Decimal(r['待核股份']) for r in rows),Decimal(0))),'股'],['现金分红',str(sum((Decimal(r['分红_CNY']) for r in rows),Decimal(0))),'CNY']]}
