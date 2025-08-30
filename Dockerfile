# Use a stable base (Debian bookworm)
FROM python:3.10-slim-bookworm

# Install system dependencies (including git)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    gnupg \
    ca-certificates \
    git \
 && curl -fsSL https://deb.nodesource.com/setup_19.x | bash - \
 && apt-get install -y nodejs \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Copy code into container
COPY . /app/
WORKDIR /app/

# Install Python dependencies
RUN python -m pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Start the bot
CMD ["bash", "start"]
