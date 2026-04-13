FROM python:3.12-slim

# Install ffmpeg for audio extraction (ad script feature)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl nodejs npm && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Ensure latest yt-dlp (bypasses lock file pinning)
RUN uv pip install --upgrade yt-dlp && uv run python -c "import yt_dlp; print('yt-dlp version:', yt_dlp.version.__version__)"

# Install Playwright Chromium browser + system dependencies
RUN uv run playwright install --with-deps chromium

# Copy application code
COPY . .

# Set environment
ENV PYTHONPATH=.
EXPOSE 8000

# Healthcheck for Railway / Docker
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run the FastAPI server
CMD ["uv", "run", "api.py"]
