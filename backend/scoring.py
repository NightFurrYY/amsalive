"""Transparent questionnaire scoring; no AI signals modify questionnaire totals."""
from typing import Literal
from pydantic import BaseModel, Field, field_validator

ADULT = [
    'I have felt tense, anxious or nervous',
    'I have felt I have someone to turn to for support when needed',
    'I have felt able to cope when things go wrong',
    'Talking to people has felt too much for me',
    'I have felt panic or terror',
    'I made plans to end my life',
    'I have had difficulty getting to sleep or staying asleep',
    'I have felt despairing or helpless',
    'I have felt unhappy',
    'Unwanted images or memories have been distressing me',
]
YOUTH = [
    "I've felt edgy or nervous", "I haven't felt like talking to anyone",
    "I've felt able to cope when things go wrong", "I've thought of hurting myself",
    "There's been someone I felt able to ask for help", "My thoughts and feelings distressed me",
    "My problems have felt too much for me", "It's been hard to go to sleep or stay asleep",
    "I've felt unhappy", "I've done all the things I wanted to",
]
REVERSE = {'adult': (1,2), 'youth': (2,4,9)}
SAFETY_INDEX = {'adult':5, 'youth':3}
BANDS = [(5,'Minimal'),(10,'Low'),(14,'Mild'),(19,'Moderate'),(24,'Moderate-to-high'),(40,'High')]

class ScoreInput(BaseModel):
    age: int = Field(ge=11, le=120)
    answers: list[int | None] = Field(min_length=10,max_length=10)
    consent: bool
    @field_validator('answers')
    @classmethod
    def valid_answers(cls, values):
        for v in values:
            if v is not None and (type(v) is not int or not 0 <= v <= 4):
                raise ValueError('Responses must be 0–4 or null for unanswered')
        return values

def score(age:int, answers:list[int | None]):
    kind='adult' if age>=17 else 'youth'
    missing=sum(v is None for v in answers)
    safety=answers[SAFETY_INDEX[kind]] is not None and answers[SAFETY_INDEX[kind]]>0
    transformed=[None if v is None else (4-v if i in REVERSE[kind] else v) for i,v in enumerate(answers)]
    # For this research prototype, missing answers mean no reported total; do not extrapolate.
    total=sum(transformed) if missing==0 else None
    label=next((name for cap,name in BANDS if total is not None and total<=cap),None) if kind=='adult' else None
    return {
        'instrument':'CORE-10 (user-provided wording; verify licensing/version)' if kind=='adult' else 'Youth 10-item prototype (not clinically validated)',
        'kind':kind,'total':total,'maximum':40,'interpretation':label if label else ('Not scored — incomplete' if missing else 'Raw score only — no validated youth cutoffs'),
        'scored_items':transformed,'missing_count':missing,'safety_response':safety,
        'diagnosis':False,'ai_used_in_score':False,
        'limitations':'Self-report screening, not a diagnosis. Confirm questionnaire rights, wording, age suitability and thresholds with a qualified professional before clinical use.'
    }
