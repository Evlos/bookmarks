FROM python:3.12-alpine

WORKDIR /app

# Build deps for lxml/socks (pysocks is pure-python, no extra needed)
RUN apk add --no-cache gcc musl-dev libffi-dev

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY templates/ templates/

# Create data dir for SQLite DB
RUN mkdir -p /data

ENV FLASK_APP=app.py
ENV DB_PATH=/data/bookmarks.db
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

# CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "app:app"]
CMD ["python", "app.py"]
