"""Train optional experimental MFCC baseline. Requires licensed labeled data.
CSV: filepath,label,speaker_id. File paths may be relative to CSV directory.
Usage: python training/train_audio.py --csv training/data.csv
"""
import argparse, csv, pathlib, joblib, numpy as np, soundfile as sf, librosa
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import GroupShuffleSplit
from backend.audio_features import features

p=argparse.ArgumentParser()
p.add_argument('--csv')
p.add_argument('--ravdess-dir',type=pathlib.Path)
p.add_argument('--prepare-only',action='store_true')
p.add_argument('--dataset',default='User-provided licensed dataset')
args=p.parse_args()
if args.ravdess_dir:
    labels={'01':'neutral','02':'calm','03':'happy','04':'sad','05':'angry','06':'fearful','07':'disgust','08':'surprised'}
    rows=[]
    for wav in sorted(args.ravdess_dir.rglob('*.wav')):
        parts=wav.stem.split('-')
        if len(parts)==7 and parts[0]=='03' and parts[1]=='01' and parts[2] in labels:
            rows.append({'filepath':str(wav.resolve()),'label':labels[parts[2]],'speaker_id':'actor_'+parts[6]})
    if len(set(r['speaker_id'] for r in rows))<5:
        raise SystemExit('RAVDESS extraction needs at least five actors')
    dest=pathlib.Path(__file__).resolve().parent/'data.csv'
    with dest.open('w',newline='',encoding='utf8') as stream:
        writer=csv.DictWriter(stream,fieldnames=['filepath','label','speaker_id'])
        writer.writeheader();writer.writerows(rows)
    print('Prepared',len(rows),'RAVDESS speech clips from',len(set(r['speaker_id'] for r in rows)),'actors:',dest)
    print('RAVDESS license CC BY-NC-SA 4.0: noncommercial research only.')
    args.csv=str(dest)
    args.dataset='RAVDESS acted speech (CC BY-NC-SA 4.0)'
    if args.prepare_only:raise SystemExit(0)
if not args.csv:p.error('Provide --csv or --ravdess-dir')
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
