FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY backend ./backend
COPY binzip/__init__.py ./binzip/__init__.py
COPY binzip/catalog_photos.py ./binzip/catalog_photos.py
COPY binzip/schemas ./binzip/schemas
COPY binzip/DATA/spaces.json ./binzip/DATA/spaces.json
COPY index.html styles.css app.js data.js ./

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
