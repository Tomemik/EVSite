FROM node:21-alpine3.18

RUN apk add --no-cache bash
RUN mkdir /code
WORKDIR /code

COPY . /code

RUN npm ci && npm cache clean --force

RUN npm run build

RUN mkdir -p /frontend_dist
RUN cp -r dist /frontend_dist

CMD ["echo", "Build complete in the image."]