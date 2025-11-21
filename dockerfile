FROM python:3.12-slim

ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY ./requirements /app/requirements
RUN pip install --upgrade pip && \
    pip install -r requirements/dev.txt

RUN apt-get update && apt-get install -y wget && \
    wget -O /usr/local/bin/wait-for-it.sh https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh && \
    chmod +x /usr/local/bin/wait-for-it.sh && \
    apt-get autoremove -y wget && \
    rm -rf /var/lib/apt/lists/*

COPY . /app

ENTRYPOINT ["/app/entrypoint.sh"]