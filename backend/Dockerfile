FROM python:3.12-slim

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Set environment
ENV PYTHONPATH=.
EXPOSE 8000

# Run the FastAPI server
CMD ["uv", "run", "api.py"]
