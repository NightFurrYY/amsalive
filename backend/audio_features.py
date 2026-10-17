import numpy as np

def features(y,sr):
    import librosa
    mfcc=librosa.feature.mfcc(y=y,sr=sr,n_mfcc=20)
    delta=librosa.feature.delta(mfcc)
    return np.concatenate([mfcc.mean(axis=1),mfcc.std(axis=1),delta.mean(axis=1)]).astype('float32')
