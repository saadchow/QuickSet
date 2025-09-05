# Chromium + Playwright included
FROM mcr.microsoft.com/playwright/python:v1.46.0-jammy

WORKDIR /app

# Install deps first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Render provides $PORT at runtime; keep a default for local runs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Start FastAPI (adjust the module path if yours isn't app/main.py)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
