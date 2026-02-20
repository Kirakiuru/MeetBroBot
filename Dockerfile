FROM python:3.12-slim

WORKDIR /app

# Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Source
COPY . .

RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]
