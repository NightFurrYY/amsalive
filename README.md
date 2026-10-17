# AMSA 2.0 Research Edition

**Status: deployable research prototype, NOT clinically validated and NOT a medical device.**

A new implementation of the Artificial Mental State Analyzer with Amy, age-aware self-report questionnaire, separate optional camera/audio analysis, PDF reporting, and a private local-only dashboard. This is a replacement for the previous broken 6,000-line HTML, not a patch of that file.

## Quick start on Windows 11 (Python 3.13)

1. Extract ZIP, open the inner `AMSA_2_0_Deploy_Ready` folder in VS Code (where `requirements.txt` is).
2. Open VS Code Terminal → PowerShell.
3. Run:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
```

4. Open `http://127.0.0.1:8000` in Chrome. API docs: `http://127.0.0.1:8000/api/docs`.
5. Use `Ctrl+C` to stop.

**If Windows blocks Activate.ps1**, run `.venv\Scripts\python.exe -m pip install -r requirements.txt` then `.venv\Scripts\python.exe -m uvicorn backend.main:app --reload` instead.

## Deploy TODAY with Render + GitHub

This package includes `Dockerfile` and `render.yaml`. **The full FastAPI project is not a static Vercel HTML upload**; use Render or another Docker/Python web host.

1. Create a new GitHub repository (prefer **private** initially) named `amsa-2`.
2. Upload all project files **inside** `AMSA_2_0_Deploy_Ready` to the repository root, including `Dockerfile`, `backend`, `frontend`, `models`, `requirements.txt`, and `render.yaml`. Do not upload `.venv`, private participant data, or credentials.
3. In [Render](https://dashboard.render.com/), choose **New → Web Service**, connect GitHub, select the repository.
4. Choose **Docker** as runtime. If asked, use Dockerfile path `./Dockerfile`. Use the lowest available instance type for testing; pricing and free availability can change.
5. Deploy. Render supplies a HTTPS URL. Visit `/api/health` to confirm `"status":"ok"`, then visit `/`.
6. If you own a domain, use Render's **Custom Domains** setting and follow its DNS instructions. Search engine appearance is not guaranteed; add public pages, an appropriate robots/sitemap strategy and Google Search Console only after reviewing the public-health claims and privacy terms.

**Important:** On the lightweight deployment, camera and microphone capture can connect, but CNN and MFCC classification results correctly display **Unavailable** until actual models are configured. This is intentional, not a broken assessment. Reports still show all three result sections. Do not describe the site as providing medical diagnoses.

## Tests

```powershell
pip install -r requirements-dev.txt
python -m pytest -q
```

Check JS syntax (if Node.js is installed): `node --check frontend/app.js`.

## Optional research-only AI models

### MFCC speech classifier

1. Use Python 3.11 for the optional ML stack if dependencies conflict with Python 3.13.
2. `pip install -r requirements-ai.txt`.
3. Prepare a **licensed and consented** dataset as CSV with `filepath,label,speaker_id`, and WAV files. Ensure speakers are separated between train and test.
4. `python training/train_audio.py --csv training/data.csv --dataset "Your licensed dataset"`.
5. The generated `models/speech_mfcc.joblib` enables local inference. Model performance must be evaluated on an external, representative dataset before claims about accuracy.

### Facial CNN

1. Install `requirements-ai.txt` in a compatible Python 3.11 environment.
2. Set environment variable `AMSA_FACE_MODEL=deepface` (PowerShell: `$env:AMSA_FACE_MODEL='deepface'`).
3. Run FastAPI. DeepFace may need internet to download model weights. A heavy CPU-only host may be slow or run out of memory.
4. Face analysis averages classifications from up to eight sampled frames. These labels describe expressions, **not a person's internal feelings, mental health, or safety**.

**Never install untrusted joblib files:** they can execute code when loaded. Use only models you trained yourself.

## Scoring and clinical boundaries

- Adults 17+: CORE-10-style questionnaire text taken from the earlier user-provided AMSA project. Reverse-code items 2 and 3; report 0–40 only for all ten completed answers. A response to the suicide-planning item triggers separate human-support guidance regardless of score.
- Ages 11–16: user-provided youth questionnaire, reverse-code items 3, 5, and 10; report raw total only, **no adult thresholds or diagnostic interpretation**.
- This project intentionally uses conservative **no total score for any missing answer** rather than extrapolating.
- The published wording, permission to reproduce questionnaire items, age appropriateness, scoring details and clinical cutoffs **must be verified by qualified reviewers** before public/clinical use. Current categories reflect prior prototype bands, not a new validation study.
- AI and Amy's free-text prompts **never change the questionnaire score**.
- Under-18 participants cannot enable recording in this prototype. A full public service for minors needs safeguarding and consent review.

## Privacy / production limitations

- The API does **not** write recordings, reports or responses to a database. PDF is generated in memory.
- The dashboard saves limited score/date/mood data in browser localStorage only when the user chooses. LocalStorage is not encrypted and is unsuitable on shared devices.
- There is no user login, cross-device syncing, clinician dashboard, independent clinical validation, or production-grade privacy/legal review.
- The rule-based Amy assistant provides generic information; it is **not** a generative AI therapist.
- Camera/microphone capture requires HTTPS or localhost. The microphone uses the browser's legacy ScriptProcessor API for broad compatibility; a production iteration should use AudioWorklet.
- Do not solicit sensitive real-user health data publicly before legal/privacy/safety and research-ethics review. For public demonstration, use synthetic/test answers.

## Architecture

- `frontend/index.html`, `styles.css`, `app.js` — browser application
- `backend/main.py` — FastAPI endpoints, optional model inference, in-memory PDF
- `backend/scoring.py` — deterministic questionnaire scoring
- `backend/audio_features.py` — optional MFCC features
- `training/train_audio.py` — optional speaker-disjoint training baseline
- `tests/test_api.py` — API, scoring, safety and PDF tests
- `Dockerfile`, `render.yaml` — deployment files

No API keys are required for the base version.
