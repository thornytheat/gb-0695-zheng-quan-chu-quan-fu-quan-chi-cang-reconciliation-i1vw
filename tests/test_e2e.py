def test_all_pages_render(client):
    for n in range(1,8): assert client.get('/work/'+str(n)).status_code==200
def test_end_to_end_idempotence(client):
    first=client.post('/api/run',json={}).get_json();again=client.post('/api/run',json={}).get_json()
    assert first['manifest']['run_id']==again['manifest']['run_id'];assert again['reused'] is True
    assert len(client.get('/api/history').get_json())==1
def test_review_rejects_stale_version(client):
    run=client.post('/api/run',json={}).get_json();payload={'id':run['manifest']['run_id'],'revision':1,'decision':'通过'}
    assert client.post('/api/review',json=payload).status_code==200
    assert client.post('/api/review',json=payload).status_code==409
def test_empty_input_is_recoverable(client):
    assert client.post('/api/run',json={'csv':''}).status_code==422
    assert client.post('/api/run',json={}).status_code==200
def test_evidence_has_manifest_and_reason(client):
    text=client.get('/api/evidence.csv').data.decode('utf-8-sig')
    assert 'run_id' in text and '规则版本' in text and '原因码' in text
def test_independent_module_endpoints(client):
    for n in range(1,8):
        response=client.post('/api/m'+str(n),json={})
        assert response.status_code==200;assert response.get_json()['stage']==n
def test_selected_batch_survives_interleaved_rerun(client,raw):
    first=client.post('/api/run',json={'csv':raw}).get_json();other=client.post('/api/run',json={'csv':raw+'\n'}).get_json();again=client.post('/api/run',json={'csv':raw}).get_json()
    assert first['manifest']['run_id']==again['manifest']['run_id']!=other['manifest']['run_id']
    ident=first['manifest']['run_id'];page=client.get('/work/4?run_id='+ident).data.decode();evidence=client.get('/api/evidence.csv?run_id='+ident).data.decode('utf-8-sig')
    assert ident in page and ident in evidence and other['manifest']['run_id'] not in evidence
def test_unknown_batch_is_404(client):
    assert client.get('/work/1?run_id=absent').status_code==404
    assert client.get('/api/evidence.csv?run_id=absent').status_code==404
def test_invalid_review_action(client):
    run=client.post('/api/run',json={}).get_json()
    assert client.post('/api/review',json={'id':run['manifest']['run_id'],'revision':1,'decision':'其他'}).status_code==422

def test_completed_registration_updates_price_and_holdings_together(client,raw):
    first=client.post('/api/run',json={'csv':raw}).get_json()
    completed=raw+'9007199254741021,position,000021,,2026-11-18,,,,,,,,210,1,0\n'
    second=client.post('/api/run',json={'csv':completed}).get_json()
    assert second['manifest']['run_id']!=first['manifest']['run_id']
    price=lambda run:[r for r in run['stages']['4']['rows'] if r['证券']=='000021'][0]
    assert price(first)['状态']=='暂定' and price(second)['状态']=='确认'
    assert price(first)['参考价_CNY']==price(second)['参考价_CNY']=='8.0000'
    hold=lambda run:[r for r in run['stages']['5']['rows'] if r['持仓记录']=='9007199254741021'][0]
    assert hold(first)['新股份']=='240' and hold(first)['待核股份']=='20'
    assert hold(second)['新股份']=='271' and hold(second)['待核股份']=='0'
    assert client.get('/api/runs/'+first['manifest']['run_id']).status_code==200
def test_rerun_never_double_counts_shares(client,raw):
    first=client.post('/api/run',json={'csv':raw}).get_json()
    extra='\nB0021,action,000021,,2026-11-15,2026-11-17,2026-11-19,10,0.1,0.2,0,0,,1,\nB0022,action,000021,,2026-11-15,2026-11-18,2026-11-19,10,0,0,0.1,5,,1,'
    second=client.post('/api/run',json={'csv':raw+extra}).get_json()
    shares=lambda run:{r['持仓记录']:r['新股份'] for r in run['stages']['5']['rows']}
    assert shares(first)==shares(second)
    assert [m for m in second['stages']['2']['metrics'] if m[0]=='重复行'][0][1]==3
def test_interrupted_recalc_preserves_previous_batch(client,raw):
    first=client.post('/api/run',json={'csv':raw}).get_json();ident=first['manifest']['run_id']
    broken=raw.replace('record,kind,security','record,kind,broken',1)
    assert client.post('/api/run',json={'csv':broken}).status_code==422
    assert client.get('/api/runs/'+ident).get_json()['manifest']['run_id']==ident
    assert client.get('/work/4?run_id='+ident).status_code==200
    assert [h['id'] for h in client.get('/api/history').get_json()]==[ident]
def test_interrupted_pipeline_leaves_store_untouched(client,raw,monkeypatch):
    first=client.post('/api/run',json={'csv':raw}).get_json();ident=first['manifest']['run_id']
    import app.pipeline as pipeline,pytest
    def boom(ctx):raise RuntimeError('复算中断')
    monkeypatch.setattr(pipeline,'STAGES',pipeline.STAGES[:4]+[boom]+pipeline.STAGES[5:])
    with pytest.raises(RuntimeError):client.post('/api/run',json={'csv':raw+'\n'})
    assert client.get('/api/runs/'+ident).status_code==200
    assert [h['id'] for h in client.get('/api/history').get_json()]==[ident]
def test_non_object_json_never_runs_default_sample(client):
    for endpoint in ['/api/run','/api/review']+['/api/m'+str(n) for n in range(1,8)]:
        for value in ([],[1],'text',7,True,None):
            response=client.post(endpoint,json=value) if value is not None else client.post(endpoint,data='null',content_type='application/json')
            assert response.status_code==400 and response.get_json()['code']=='REQUEST'
    assert client.get('/api/history').get_json()==[]

def test_malformed_or_non_json_is_bad_request(client):
    assert client.post('/api/run',data='{',content_type='application/json').status_code==400
    assert client.post('/api/run',data='csv=text').status_code==400

def test_wrong_upload_field_is_bad_request(client):
    import io
    assert client.post('/api/run',data={'wrong':(io.BytesIO(b'a,b'),'wrong.csv')}).status_code==400

def test_uploaded_dates_are_current_in_page_and_csv(client,raw):
    content=raw.replace('2026-11-17','2026-12-17').replace('2026-11-18','2026-12-18').replace('2026-11-19','2026-12-19')
    run=client.post('/api/run',json={'csv':content}).get_json();ident=run['manifest']['run_id']
    page=client.get('/work/3?run_id='+ident).data.decode()
    assert '登记 2026-12-17' in page and '除权 2026-12-18' in page and '2026-12-19' in page
    assert run['stages']['3']['metrics'][2][1]=='2026-12-17 / 2026-12-18'
    evidence=client.get('/api/evidence.csv?run_id='+ident).data.decode('utf-8-sig')
    assert '2026-12-19' in evidence and ident in evidence

def test_rule_version_is_part_of_batch_identity(monkeypatch):
    import app.manifest as manifest
    first=manifest.make('same content')
    monkeypatch.setattr(manifest,'RULE_VERSION','future-rules')
    second=manifest.make('same content')
    assert first['sha256']==second['sha256'] and first['run_id']!=second['run_id']
