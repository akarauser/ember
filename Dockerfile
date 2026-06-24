FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl ca-certificates libgl1 libglib2.0-0

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY . /app/

RUN uv sync --locked

EXPOSE 8501

CMD ["uv", "run", "streamlit", "run", "src/ember/main.py", "--server.port=8501", "--server.address=0.0.0.0"]