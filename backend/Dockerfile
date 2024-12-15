FROM python:3.11.5-slim
ENV PYTHONBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

ENV ENV=${ENV}

RUN apt-get update && \
    apt-get -y install libpq-dev gcc procps cron nano && \
    apt-get autoremove && rm -r /var/lib/apt/lists/*

RUN mkdir /code
WORKDIR /code
COPY . /code

RUN pip install --no-cache-dir -r requirements.txt;

COPY cronjob /etc/cron.d/imports
RUN chmod 0644 /etc/cron.d/imports

RUN crontab /etc/cron.d/imports