from app.pipeline import calculate
def event(ctx):return[e for e in ctx['events'] if e['canonical']=='000021'][0]
def holding(ctx,record):return[r for r in ctx['holdings'] if r['持仓记录']==record][0]
def factor_row(ctx,security='000021'):return[r for r in ctx['stages']['4']['rows'] if r['证券']==security][0]
def test_announcements_compose_single_event(ctx):
    e=event(ctx)
    assert e['record']=='B0021+B0022' and e['record_dates']==['2026-11-17','2026-11-18']
    assert str(e['cash'])=='0.1' and str(e['bonus'])=='0.2' and str(e['rights'])=='0.1' and str(e['rights_price'])=='5'
def test_components_keep_distinct_record_dates(ctx):
    assert{c['record']:c['record_date'] for c in event(ctx)['components']}=={'B0021':'2026-11-17','B0022':'2026-11-18'}
def test_pending_registration_marked_per_investor(ctx):
    status={(e['position']['record'],e['action']['record']):e['status'] for e in ctx['eligible'] if e['event']['canonical']=='000021'}
    assert status[('9007199254741021','B0021')]=='已核'
    assert status[('9007199254741021','B0022')]=='待核'
    assert status[('9007199254741022','B0022')]=='已核'
def test_each_component_uses_own_record_date_snapshot(ctx):
    snaps={e['action']['record']:e['position']['event_date'] for e in ctx['eligible'] if e['position']['record']=='9007199254741022'}
    assert snaps=={'B0021':'2026-11-17','B0022':'2026-11-18'}
def test_reference_price_published_from_announcements(ctx):
    row=factor_row(ctx)
    assert row['参考价_CNY']=='8.0000' and row['参考价采用']=='B0021+B0022'
    assert row['状态']=='暂定' and row['持仓采用']=='B0021+B0022' and row['待核行动']=='B0022×1'
def test_fully_registered_events_are_final(ctx):
    assert all(r['状态']=='确认' for r in ctx['stages']['4']['rows'] if r['证券']!='000021')
def test_pending_rights_withheld_from_shares(ctx):
    h=holding(ctx,'9007199254741021')
    assert h['新股份']=='240' and h['待核股份']=='20' and h['状态']=='部分待核'
    assert h['认配支付_CNY']=='0.00' and h['待核认配_CNY']=='100.00'
def test_confirmed_investor_booked_in_full(ctx):
    h=holding(ctx,'9007199254741022')
    assert h['新股份']=='445' and h['待核股份']=='0' and h['认配支付_CNY']=='175.00' and h['状态']=='已核'
def test_conflicting_components_isolated(raw):
    conflict=raw+'\nB0021,action,000021,,2026-11-15,2026-11-17,2026-11-19,99,0.1,0.2,0,0,,2,'
    result=calculate(conflict)
    assert all(e['canonical']!='000021' for e in result['events'])
    assert any(q['原因码']=='CONFLICT' and q.get('record')=='B0021' for q in result['quarantine'])
def test_late_registration_completes_price_and_holdings(raw):
    completed=raw+'9007199254741021,position,000021,,2026-11-18,,,,,,,,210,1,0\n'
    before,after=calculate(raw),calculate(completed)
    assert factor_row(before)['状态']=='暂定' and factor_row(after)['状态']=='确认'
    assert factor_row(before)['参考价_CNY']==factor_row(after)['参考价_CNY']=='8.0000'
    assert holding(before,'9007199254741021')['新股份']=='240'
    assert holding(after,'9007199254741021')['新股份']=='271'
    assert holding(after,'9007199254741021')['待核股份']=='0'
def test_duplicate_announcements_never_double_count(raw):
    extra='\nB0021,action,000021,,2026-11-15,2026-11-17,2026-11-19,10,0.1,0.2,0,0,,1,\nB0022,action,000021,,2026-11-15,2026-11-18,2026-11-19,10,0,0,0.1,5,,1,'
    shares=lambda ctx:{r['持仓记录']:r['新股份'] for r in ctx['holdings']}
    assert shares(calculate(raw))==shares(calculate(raw+extra))
    assert calculate(raw+extra)['duplicates']==3
