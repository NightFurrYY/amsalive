from fastapi.testclient import TestClient
from backend.main import app
from backend.scoring import score

client=TestClient(app)
def test_health():
    r=client.get('/api/health');assert r.status_code==200 and r.json()['clinical_validation'] is False

def test_homepage():
    r=client.get('/');assert r.status_code==200 and 'AMSA' in r.text

def test_scoring_reversal():
    x=score(21,[0]*10);assert x['total']==8 and x['safety_response'] is False
    x=score(21,[0,4,4,0,0,0,0,0,0,0]);assert x['total']==0

def test_safety_not_overridden():
    x=score(21,[0,4,4,0,0,1,0,0,0,0]);assert x['total']==1 and x['safety_response']

def test_missing_not_scored():
    x=score(21,[None]+[0]*9);assert x['total'] is None

def test_youth_no_clinical_band():
    x=score(15,[0]*10);assert x['total']==12 and x['interpretation'].startswith('Raw score')

def test_consent_required():
    r=client.post('/api/questionnaire/score',json={'age':21,'answers':[0]*10,'consent':False});assert r.status_code==403

def test_invalid_answers():
    r=client.post('/api/questionnaire/score',json={'age':21,'answers':[0]*9+[7],'consent':True});assert r.status_code==422

def test_pdf_contains_pdf_bytes():
    data={'name':'Test Participant','age':21,'date':'2026-10-17','answers':[0,4,4,0,0,0,0,0,0,0],
          'intro':{'day':'Fine','feeling':'Okay'},'face':{'status':'unavailable','reason':'No model'},
          'audio':{'status':'unavailable','reason':'No model'},'consent':True}
    r=client.post('/api/report/pdf',json=data)
    assert r.status_code==200 and r.content.startswith(b'%PDF') and len(r.content)>1000

def test_models_absent_do_not_fabricate():
    r=client.post('/api/face/analyze-session',data={'consent':'true'},files=[('files',('f.jpg',b'not an image','image/jpeg'))]);assert r.status_code==200 and r.json()['status']=='unavailable'
    r=client.post('/api/audio/analyze',data={'consent':'true'},files={'file':('f.wav',b'fake','audio/wav')});assert r.status_code==200 and r.json()['status']=='unavailable'
