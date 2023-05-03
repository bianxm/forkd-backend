FROM python:3.10
RUN useradd forkdflask
WORKDIR /home/forkdflask

RUN apt update
RUN apt install -y libpq-dev gcc

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY api_server.py model.py permissions_helper.py ./
RUN chown -R forkdflask:forkdflask ./
USER forkdflask

EXPOSE 5000
CMD ["gunicorn","-b",":5000","api_server:app"]