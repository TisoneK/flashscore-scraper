# ── Railway Dockerfile for Flashscore Scraper ──────────────────────
# Builds a Python image with Chrome headless pre-installed.
# The scraper runs as a scheduled cron job via Railway's cron worker.

FROM python:3.12-slim

# Avoid interactive prompts during package install
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# ── Install Chrome + dependencies ─────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg2 \
    unzip \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    xdg-utils \
    # Required for headless Chrome
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Add Google Chrome repo and install
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | \
    gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Verify Chrome
RUN google-chrome --version

# ── Install Python dependencies ───────────────────────────────────
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Install the package itself (makes `flashscore-scraper` CLI available)
RUN pip install --no-cache-dir -e .

# Create output directories
RUN mkdir -p /app/output/json /app/output/logs

# ── Default: run the Railway scraper ──────────────────────────────
# This is overridden by railway.toml cron commands
CMD ["python", "run_scraper_railway.py"]
