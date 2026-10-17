FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 AMSA_FACE_MODEL=off OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir numpy librosa soundfile scikit-learn joblib
COPY backend ./backend
COPY training ./training
COPY frontend ./frontend
COPY models ./models
RUN python -c "import urllib.request; urllib.request.urlretrieve('https://zenodo.org/records/11063852/files/Audio_Speech_Actors_01-24_16k.zip?download=1','/tmp/ravdess.zip')" && \
    python -c "import zipfile; zipfile.ZipFile('/tmp/ravdess.zip').extractall('/tmp/ravdess')" && \
    PYTHONPATH=/app python training/train_audio.py --ravdess-dir /tmp/ravdess && \
    rm -rf /tmp/ravdess /tmp/ravdess.zip
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
