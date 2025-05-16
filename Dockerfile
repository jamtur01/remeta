FROM python:3.9-slim

LABEL maintainer="remeta"
LABEL description="Tool to refresh metadata for Jellyfin items"

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy script
COPY remeta.py .
RUN chmod +x remeta.py

# Set environment variables (can be overridden at runtime)
ENV JELLYFIN_HOST=""
ENV JELLYFIN_API_KEY=""
ENV JELLYFIN_USER_ID=""

# Run the script
ENTRYPOINT ["python", "remeta.py"]