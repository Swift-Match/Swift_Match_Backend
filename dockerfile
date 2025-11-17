FROM python:3.12-slim

ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY ./requirements /app/requirements
RUN pip install --upgrade pip && \
    pip install -r requirements/dev.txt

COPY . /app

COPY ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
