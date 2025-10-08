FROM python:3.11-slim

ARG MODEL_DIR=model_artifacts
ENV MODEL_PATH=/models/model.pkl
ENV BASELINE_PATH=/models/baseline.npy
ENV EXPECTATIONS_PATH=/models/expectations.json
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY app /app/app
RUN pip install --no-cache-dir fastapi uvicorn[standard] joblib numpy prometheus-client requests great-expectations

RUN mkdir -p /models
COPY ${MODEL_DIR}/model.pkl /models/model.pkl
COPY ${MODEL_DIR}/baseline.npy /models/baseline.npy
COPY ${MODEL_DIR}/expectations.json /models/expectations.json

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
