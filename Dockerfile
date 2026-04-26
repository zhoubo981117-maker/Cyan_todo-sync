FROM python:3.12-slim

WORKDIR /app

COPY server.py /app/server.py
COPY web /app/web

ENV TODO_HOST=0.0.0.0
ENV TODO_PORT=8787

EXPOSE 8787

CMD ["python", "server.py"]

