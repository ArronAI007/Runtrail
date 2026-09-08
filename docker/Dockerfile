FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir ".[ui,gateway,postgres]"

EXPOSE 8000
CMD ["runtrail", "ui", "--host", "0.0.0.0"]
