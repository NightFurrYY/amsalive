"""Train optional experimental MFCC baseline. Requires licensed labeled data.
CSV: filepath,label,speaker_id. File paths may be relative to CSV directory.
Usage: python training/train_audio.py --csv training/data.csv
"""
import argparse, csv, pathlib, joblib, numpy as np, soundfile as sf, librosa
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import GroupShuffleSplit
from backend.audio_features import features

p=argparse.ArgumentParser();p.add_argument('--csv',required=True);p.add_argument('--dataset',default='User-provided licensed dataset');args=p.parse_args()
base=pathlib.Path(args.csv).resolve().parent
X=[];y=[];groups=[]
with open(args.csv,newline='',encoding='utf8') as f:
    for row in csv.DictReader(f):
        path=pathlib.Path(row['filepath']);path=path if path.is_absolute() else base/path
        audio,sr=sf.read(str(path),dtype='float32')
        if audio.ndim>1:audio=audio.mean(axis=1)
        if len(audio)<sr:continue
        audio=librosa.resample(audio[:sr*30],orig_sr=sr,target_sr=16000)
        X.append(features(audio,16000));y.append(row['label']);groups.append(row['speaker_id'])
if len(set(groups))<5 or len(set(y))<2:raise SystemExit('Need at least five distinct speakers and two labels')
X=np.array(X);y=np.array(y);groups=np.array(groups)
train,test=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=42).split(X,y,groups))
model=RandomForestClassifier(n_estimators=250,class_weight='balanced',random_state=42)
model.fit(X[train],y[train]);pred=model.predict(X[test]);print('Held-out speaker evaluation:');print(classification_report(y[test],pred,zero_division=0))
print('NOTE: This is not independent external validation; do not treat class probabilities as calibrated.')
out=pathlib.Path(__file__).resolve().parent.parent/'models'/'speech_mfcc.joblib';joblib.dump({'model':model,'dataset':args.dataset},out);print('Saved:',out)
