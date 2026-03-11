FROM python:3.12-slim

# System deps for cairosvg
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libcairo2-dev \
        libffi-dev \
        pkg-config && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gen_jigsaw.py svg_to_ipuz.py extract_pieces.py create_puzzle_pack.py service.py ./

EXPOSE 8080

CMD ["uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8080"]
