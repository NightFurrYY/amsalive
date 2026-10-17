from __future__ import annotations
import io, os, json, logging
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from xml.sax.saxutils import escape
from backend.scoring import ScoreInput, score, ADULT, YOUTH

ROOT=Path(__file__).resolve().parent.parent
app=FastAPI(title='AMSA 2.0 Research API',version='2.0.0',docs_url='/api/docs',openapi_url='/api/openapi.json')
MAX_BYTES=7*1024*1024
logger=logging.getLogger(__name__)

@app.get('/api/health')
def health():
    return {'status':'ok','version':'2.0.0','clinical_validation':False,
            'face_model':'enabled' if os.getenv('AMSA_FACE_MODEL','off')=='deepface' else 'disabled',
            'speech_model':'available' if (ROOT/'models'/'speech_mfcc.joblib').is_file() else 'not_trained',
            'storage':'no server-side participant history'}

@app.get('/api/questionnaire/{age}')
def questionnaire(age:int):
    if not 11<=age<=120:raise HTTPException(422,'Age must be 11–120')
    return {'items':ADULT if age>=17 else YOUTH,'kind':'adult' if age>=17 else 'youth',
            'options':['Not at all','Only occasionally','Sometimes','Often','Most or all of the time'],
            'notice':'User-supplied instrument wording. Verify authorized use before public/clinical deployment.'}

@app.post('/api/questionnaire/score')
def score_api(req:ScoreInput):
    if not req.consent:raise HTTPException(403,'Assessment consent required')
    return score(req.age,req.answers)

async def read_upload(file:UploadFile):
    data=await file.read(MAX_BYTES+1)
    if not data:raise HTTPException(422,'Empty recording')
    if len(data)>MAX_BYTES:raise HTTPException(413,'Recording too large')
    return data

@app.post('/api/face/analyze')
async def face_analyze(file:UploadFile=File(...),consent:bool=Form(False)):
    if not consent:raise HTTPException(403,'Separate facial-analysis consent required')
    if os.getenv('AMSA_FACE_MODEL','off')!='deepface':
        return {'status':'unavailable','reason':'CNN not enabled on this deployment','model':'none','diagnosis':False}
    from PIL import Image, UnidentifiedImageError
    import numpy as np
    data=await read_upload(file)
    try:
        im=Image.open(io.BytesIO(data));im.verify()
        im=Image.open(io.BytesIO(data)).convert('RGB');im.thumbnail((1024,1024))
    except (UnidentifiedImageError,ValueError,OSError):raise HTTPException(422,'Invalid image')
    try:
        from deepface import DeepFace
        res=DeepFace.analyze(img_path=np.asarray(im),actions=['emotion'],detector_backend='opencv',enforce_detection=True,silent=True)
        res=res[0] if isinstance(res,list) else res
        return {'status':'analyzed','label':str(res['dominant_emotion']),
                'scores':{str(k):round(float(v),2) for k,v in res['emotion'].items()},
                'model':'DeepFace emotion CNN','diagnosis':False,
                'warning':'Expression labels are model outputs, not mental-health measurements or calibrated clinical probabilities.'}
    except ValueError:
        return {'status':'unavailable','reason':'No face detected or image quality insufficient','diagnosis':False}
    except Exception:
        logger.exception('Facial model inference failed')
        return {'status':'unavailable','reason':'Facial model failed to initialize or infer','diagnosis':False}

@app.post('/api/audio/analyze')
async def audio_analyze(file:UploadFile=File(...),consent:bool=Form(False)):
    if not consent:raise HTTPException(403,'Separate audio-analysis consent required')
    path=ROOT/'models'/'speech_mfcc.joblib'
    if not path.is_file():
        return {'status':'unavailable','reason':'MFCC classifier has not been trained','model':'none','diagnosis':False}
    data=await read_upload(file)
    try:
        import soundfile as sf, librosa, numpy as np, joblib
        from backend.audio_features import features
        y,sr=sf.read(io.BytesIO(data),dtype='float32')
        if y.ndim>1:y=y.mean(axis=1)
        if sr<8000 or len(y)<sr:raise ValueError('At least one second of audio required')
        if len(y)>sr*35:y=y[:sr*35]
        if float(np.sqrt(np.mean(y*y)))<0.002:raise ValueError('Audio too quiet')
        x=features(librosa.resample(y,orig_sr=sr,target_sr=16000),16000).reshape(1,-1)
        bundle=joblib.load(path)
        model=bundle['model']
        label=str(model.predict(x)[0]); scores={}
        if hasattr(model,'predict_proba'):
            scores={str(k):round(float(v)*100,1) for k,v in zip(model.classes_,model.predict_proba(x)[0])}
        return {'status':'analyzed','label':label,'scores':scores,'model':'MFCC + trained classifier',
                'dataset':bundle.get('dataset','unspecified'),'diagnosis':False,
                'warning':'Speech labels are exploratory and may not generalize to different speakers, languages or microphones.'}
    except Exception as exc:
        logger.warning('Audio inference unavailable: %s',type(exc).__name__)
        return {'status':'unavailable','reason':'Unable to decode or classify this recording','diagnosis':False}

class ReportInput(BaseModel):
    name: str = Field(max_length=80)
    age: int = Field(ge=11,le=120)
    date: str = Field(max_length=50)
    answers: list[int | None] = Field(min_length=10,max_length=10)
    intro: dict[str,str] = Field(default_factory=dict)
    face: dict = Field(default_factory=dict)
    audio: dict = Field(default_factory=dict)
    consent: bool

@app.post('/api/report/pdf')
def pdf_report(req:ReportInput):
    if not req.consent:raise HTTPException(403,'Report consent required')
    # Recalculate questionnaire on server; never trust a client-supplied score.
    ScoreInput(age=req.age, answers=req.answers, consent=True)
    result=score(req.age,req.answers)
    buf=io.BytesIO();doc=SimpleDocTemplate(buf,pagesize=(595,842),leftMargin=45,rightMargin=45,topMargin=45,bottomMargin=45)
    styles=getSampleStyleSheet();styles['Title'].textColor=colors.HexColor('#4c37ae')
    story=[Paragraph('AMSA | Research Assessment Report',styles['Title']),Spacer(1,10),
           Paragraph('Experimental wellness screening — NOT a medical diagnosis',styles['Heading3']),Spacer(1,14)]
    def line(key,value):
        story.append(Paragraph(f'<b>{escape(str(key))}:</b> {escape(str(value))}',styles['BodyText']));story.append(Spacer(1,7))
    line('Participant',req.name or 'Anonymous');line('Age',req.age);line('Date',req.date)
    story.append(Paragraph('Questionnaire',styles['Heading2']))
    line('Instrument',result['instrument']);line('Score',str(result['total'])+'/40' if result['total'] is not None else 'Not scored (incomplete)')
    line('Interpretation',result['interpretation']);line('Safety response', 'Follow-up indicated; do not rely on this tool' if result['safety_response'] else 'No positive response to the designated safety item')
    story.append(Paragraph('Amy introduction (self-report)',styles['Heading2']))
    for k in ('day','feeling'):
        line(k.capitalize(),str(req.intro.get(k,'Not provided'))[:350])
    story.append(Paragraph('Supplementary experimental observations',styles['Heading2']))
    for title,obs in [('Facial expression',req.face),('Speech characteristics',req.audio)]:
        status=str(obs.get('status','unavailable'))
        label=str(obs.get('label','Not available')) if status=='analyzed' else str(obs.get('reason','Not collected'))
        line(title,f'{status}: {label[:180]}')
        if status=='analyzed':line('Model',str(obs.get('model','Unspecified'))[:90])
    story.append(Spacer(1,14));story.append(Paragraph('Important limitations',styles['Heading2']))
    story.append(Paragraph('Questionnaire results are self-report screening information, not a diagnosis. Facial and speech models are exploratory; they cannot establish a person’s mental state, honesty, psychiatric condition or safety. Model scores must not be added to the questionnaire score. Seek qualified professional assessment for concerns. If there is immediate danger, contact local emergency services.',styles['BodyText']))
    story.append(Spacer(1,12));story.append(Paragraph('Privacy: this server creates the PDF in memory and does not save the report or recordings. Local browser history is stored only if the participant chooses to save it.',styles['BodyText']))
    doc.build(story);buf.seek(0)
    return StreamingResponse(buf,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="AMSA_Assessment_Report.pdf"','Cache-Control':'no-store'})


@app.post('/api/face/analyze-session')
async def face_session(files:list[UploadFile]=File(...),consent:bool=Form(False)):
    if not consent:raise HTTPException(403,'Separate facial-analysis consent required')
    if len(files)>8:raise HTTPException(422,'Maximum eight frames')
    if os.getenv('AMSA_FACE_MODEL','off')!='deepface':
        return {'status':'unavailable','reason':'CNN not enabled on this deployment','frames_received':len(files),'diagnosis':False}
    results=[]
    for file in files:
        res=await face_analyze(file,True)
        if res.get('status')=='analyzed':results.append(res)
    if not results:return {'status':'unavailable','reason':'No analyzable faces detected','frames_received':len(files),'diagnosis':False}
    keys=set().union(*(r['scores'].keys() for r in results))
    means={k:round(sum(r['scores'].get(k,0) for r in results)/len(results),2) for k in keys}
    return {'status':'analyzed','label':max(means,key=means.get),'scores':means,'frames_analyzed':len(results),
            'frames_received':len(files),'model':'DeepFace emotion CNN (frame-mean)','diagnosis':False,
            'warning':'Averaged frame classifications describe observed expressions only; they cannot establish emotional or mental-health state.'}

app.mount('/',StaticFiles(directory=str(ROOT/'frontend'),html=True),name='frontend')
