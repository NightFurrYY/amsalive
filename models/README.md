No pretrained or trained AI model is bundled. AMSA must never fabricate model outputs.

To use the optional MFCC classifier locally: install requirements-ai.txt and run training/train_audio.py with a licensed, consented, labeled WAV dataset; the script creates models/speech_mfcc.joblib. Validate speaker-disjoint and independent test performance before interpreting results.

To use DeepFace facial expression inference locally: install requirements-ai.txt and set AMSA_FACE_MODEL=deepface. DeepFace may download model weights. Never describe its expression labels as mental-health diagnosis. Default Docker deployment keeps this off to remain lightweight.
