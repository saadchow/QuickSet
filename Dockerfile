# Uses Ubuntu Jammy with Playwright 1.46 + browsers preinstalled
FROM mcr.microsoft.com/playwright/python:v1.46.0-jammy

WORKDIR /app

# Install Python deps (playwright is already included in the base image)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

EXPOSE 8000
# If you protect /refresh with a token, leave uvicorn as-is.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
