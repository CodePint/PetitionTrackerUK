
FROM node:latest as build

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
COPY package.json /usr/src/app

RUN yarn install
COPY . /usr/src/app
RUN yarn run build

FROM xqdocker/ubuntu-nginx
COPY --from=build /usr/src/app/build /usr/share/nginx/html
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]