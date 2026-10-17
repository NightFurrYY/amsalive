No pretrained or trained AI model is bundled. AMSA must never fabricate model outputs.

To use the optional MFCC classifier locally: install requirements-ai.txt and run training/train_audio.py with a licensed, consented, labeled WAV dataset; the script creates models/speech_mfcc.joblib. Validate speaker-disjoint and independent test performance before interpreting results.

To use DeepFace facial expression inference locally: install requirements-ai.txt and set AMSA_FACE_MODEL=deepface. DeepFace may download model weights. Never describe its expression labels as mental-health diagnosis. Default Docker deployment keeps this off to remain lightweight.

Research dataset option: RAVDESS speech, https://zenodo.org/records/1188976 . Its CC BY-NC-SA 4.0 license restricts commercial use; obtain appropriate rights before commercial deployment. Use speaker-disjoint validation and report held-out results. Acted emotion labels do not establish mental health.

Render: the default Dockerfile installs only requirements.txt and sets AMSA_FACE_MODEL=off. To enable facial inference, an alternative build must install compatible DeepFace dependencies and set AMSA_FACE_MODEL=deepface; confirm memory requirements and licensing first. To enable speech inference, build and bundle models/speech_mfcc.joblib from licensed labeled recordings. Do not claim either model is running until /api/health and real endpoint tests confirm it.
