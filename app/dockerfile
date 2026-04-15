# Use official lightweight Python image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements first (so Docker caches this layer)
COPY requirements.txt .

# Install all packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY app/ ./app/

# Expose the gateway port
EXPOSE 8000

# Start the gateway when container runs
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]