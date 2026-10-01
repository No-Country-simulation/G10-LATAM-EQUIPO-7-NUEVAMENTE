FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY data_ai ./data_ai

EXPOSE 8002

CMD ["uvicorn", "data_ai.api.app:app", "--host", "0.0.0.0", "--port", "8002"]