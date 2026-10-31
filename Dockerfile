# Production Dockerfile for P5 - Report Navigator
# Multi-language runtime: Node.js 20 + Python 3.11 + Tesseract OCR + Poppler

FROM node:20-bookworm-slim

# Install system packages: Python 3, Tesseract OCR, Poppler utils
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    poppler-utils \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set container working directory
WORKDIR /app

# Create Python virtual environment and put it on PATH
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy package manifests first for build caching
COPY package.json package-lock.json ./
COPY solution/requirements.txt ./solution/requirements.txt

# Install Python requirements in virtual environment
RUN pip install --no-cache-dir -r solution/requirements.txt

# Install Node dependencies (including devDependencies required for vite build)
RUN npm ci

# Copy application source code
COPY . .

# Build Vite frontend into /app/dist
RUN npm run build

# Expose default application port
EXPOSE 3000

# Production environment variables
ENV NODE_ENV=production
ENV PORT=3000

# Start Express server (runs Vite dist static files & spawns Python backend daemon)
CMD ["npm", "start"]
