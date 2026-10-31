FROM python:3.10-slim

# Mencegah Python buffering output agar log langsung tampil realtime di docker logs
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install fonts-dejavu untuk render tanda ceklis (✓) pada PDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "run.py"]
