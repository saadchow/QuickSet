FROM python:3.11-slim

# System deps for Playwright Chromium
RUN apt-get update && apt-get install -y     curl ca-certificates fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0     libcups2 libdbus-1-3 libdrm2 libexpat1 libgbm1 libglib2.0-0 libgtk-3-0     libnspr4 libnss3 libpango-1.0-0 libx11-6 libx11-xcb1 libxcb1 libxcomposite1     libxdamage1 libxext6 libxfixes3 libxkbcommon0 libxrandr2 xdg-utils     && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt     && playwright install --with-deps chromium

COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
