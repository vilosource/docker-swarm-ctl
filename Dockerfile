# Stage 1: Build Stage
FROM python:3.12-slim as builder

# Install poetry
RUN pip install poetry

# Set up a non-root user
RUN groupadd -g 1001 docker && useradd --create-home -u 1000 -g docker appuser
WORKDIR /home/appuser

# Copy only dependency definition files
COPY pyproject.toml poetry.lock README.md ./

# Install dependencies into a virtual environment
RUN poetry config virtualenvs.in-project true && poetry install

# Stage 2: Final Stage
FROM python:3.12-slim

# Set up a non-root user
RUN groupadd -g 1001 docker && useradd --create-home -u 1000 -g docker appuser
USER appuser
WORKDIR /home/appuser

# Copy virtual environment from builder
COPY --from=builder /home/appuser/.venv .venv
ENV PATH="/home/appuser/.venv/bin:$PATH"

# Copy application code
COPY dsctl_server/ ./dsctl_server/

# Expose the port the app runs on
EXPOSE 8000

# Run the application
CMD ["uvicorn", "dsctl_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
