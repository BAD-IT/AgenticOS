FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv for rapid package resolution
RUN pip install --no-cache-dir uv

COPY requirements-prod.txt requirements-dev.txt ./
# Install dependencies into the system python
RUN uv pip install --system -r requirements-dev.txt

# Do not copy all files yet, source code will be bind-mounted via docker-compose for hot-reloading
# But we copy the rest to have the structure
COPY . .
