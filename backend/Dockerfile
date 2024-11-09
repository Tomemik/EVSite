FROM python:3.11.5-slim
ENV PYTHONBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

ENV ENV=${ENV}

RUN apt-get update && \
    apt-get -y install libpq-dev gcc procps && \
    apt-get autoremove && rm -r /var/lib/apt/lists/*

RUN mkdir /app
WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt;
