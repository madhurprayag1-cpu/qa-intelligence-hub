FROM python:3.13-slim
WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app
COPY qa-engine /app/qa-engine
COPY ai-engine /app/ai-engine
COPY test-data /app/test-data

RUN ln -s /app/qa-engine /qa-engine && \
    ln -s /app/ai-engine /ai-engine && \
    chmod +x /app/entrypoint.sh

ENV PYTHONPATH=/app:/app/qa-engine:/app/ai-engine
EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
