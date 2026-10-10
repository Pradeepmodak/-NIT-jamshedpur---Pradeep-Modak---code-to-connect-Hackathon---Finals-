FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose API and Streamlit ports
EXPOSE 8000
EXPOSE 8501

# Default command: run the API (can be overridden to run streamlit)
CMD ["uvicorn", "engine.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
