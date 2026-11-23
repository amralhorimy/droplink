FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY workers ./workers

# Never run as root inside the container.
RUN useradd --system --uid 10001 droplink
USER droplink

# One image, three roles. docker-compose.yml picks the command:
#   api       -> uvicorn app.main:app
#   processor -> python -m workers.processor
#   janitor   -> python -m workers.janitor
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-access-log"]
