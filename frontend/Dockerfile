FROM node:21-alpine3.18
RUN apk add --no-cache bash

RUN mkdir /code
WORKDIR /code
COPY . /code
RUN npm ci && npm cache clean --force