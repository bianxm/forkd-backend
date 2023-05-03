# build stage
FROM python:3.10-slim AS builder

RUN apt update && apt install -y libpq-dev gcc

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# operational stage
FROM python:3.10-slim

RUN useradd forkdflask
WORKDIR /home/forkdflask

RUN apt update && apt install -y libpq-dev

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY api_server.py model.py permissions_helper.py ./
RUN chown -R forkdflask:forkdflask ./
USER forkdflask

EXPOSE 5000
CMD ["gunicorn","-b",":5000","api_server:app"]