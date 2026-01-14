# Production Dockerfile for HireLink
# Optimised for Render.com / Railway / Cloud Engines

FROM python:3.11-slim

# 1. Install System Dependencies & Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libxss1 \
    libasound2 \
    libxtst6 \
    libappindicator3-1 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Google Chrome (Latest Stable)
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# 3. Set Working Directory
WORKDIR /app

# 4. Copy Requirements first for better caching
COPY requirements.txt .

# 5. Install Python Dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy Project Files
COPY . .

# 7. Set Environment Variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8501

# 8. Expose Streamlit Port
EXPOSE 8501

# 9. Healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# 10. Start Application
CMD ["python3", "-m", "streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
