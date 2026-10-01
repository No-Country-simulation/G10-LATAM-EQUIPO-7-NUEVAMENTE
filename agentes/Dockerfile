FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY agentes/requirements.txt ./requirements.txt

# PyTorch solo CPU: evitamos arrastrar dependencias CUDA enormes
RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch

RUN pip install --no-cache-dir -r requirements.txt

COPY agentes ./agentes

EXPOSE 8001

CMD ["uvicorn", "agentes.api:app", "--host", "0.0.0.0", "--port", "8001"]