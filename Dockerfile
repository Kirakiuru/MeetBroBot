FROM python:3.12-slim

WORKDIR /app

# Dependencies (as root, before switching user)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN addgroup --system app && adduser --system --ingroup app app

# Source
COPY --chown=app:app . .
RUN chmod +x entrypoint.sh

USER app

CMD ["./entrypoint.sh"]
