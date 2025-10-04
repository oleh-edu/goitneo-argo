ARG PYTHON_VERSION=3.13-slim
FROM python:${PYTHON_VERSION}

WORKDIR /app

# system deps for building numpy/scikit-learn (gcc, g++)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gfortran \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# copy application source and environment file
COPY main.py /app/main.py
COPY .env /app/.env
COPY expectations.json /app/expectations.json

# ensure a non-root user runs the app
# (create a user with a fixed UID/GID )
RUN addgroup --system app && adduser --system --ingroup app app \
    && chown -R app:app /app
USER app

# application configuration
ARG APP_PORT=8080
ENV PORT=${APP_PORT}

EXPOSE ${PORT}

# uvicorn entrypoint with overridable arguments
ENTRYPOINT ["uvicorn"]
CMD ["main:app", "--host", "0.0.0.0", "--port", "${PORT}"]
