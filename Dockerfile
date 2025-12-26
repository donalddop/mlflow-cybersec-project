FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml uv.lock ./
COPY config/ ./config/
COPY src/ ./src/
COPY run_web.py ./
COPY run.py ./

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Install Python dependencies
RUN uv sync --frozen

# Expose port
EXPOSE 8000

# Run the web application
CMD ["uv", "run", "python", "run_web.py"]
