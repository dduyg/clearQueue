# Hugging Face Spaces (Docker SDK) entry point.
# Spaces expect the app to listen on port 7860 by default.

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first so Docker can cache this layer between rebuilds
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the whole project, preserving the backend/ + static/ + sample_data/ layout
COPY . .

WORKDIR /app/backend

EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
