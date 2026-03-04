FROM python:3.12-slim

# Install ffmpeg for audio extraction (ad script feature)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Install Playwright Chromium browser + system dependencies
RUN uv run playwright install --with-deps chromium

# Copy application code
COPY . .

# Set environment
ENV PYTHONPATH=.
EXPOSE 8000

# Run the FastAPI server
CMD ["uv", "run", "api.py"]
