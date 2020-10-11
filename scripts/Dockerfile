FROM ubuntu:20.04
RUN apt-get update && apt-get install -y \ 
python3-pip \
libpq-dev python3-dev

RUN pip3 install --upgrade pip
RUN pip install pipenv

ENV PROJECT_DIR /usr/src/application
RUN mkdir -p ${PROJECT_DIR}
RUN mkdir -p /usr/src/logs/app
RUN mkdir -p /usr/src/logs/celery

WORKDIR /usr/src
COPY Pipfile Pipfile.lock .env .docker.dev.env .prod.env .dev.env /usr/src/
COPY scripts /usr/src
RUN pipenv install --system --deploy

ENTRYPOINT [ "" ]
