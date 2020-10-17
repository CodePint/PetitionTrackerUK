FROM ubuntu:20.04

RUN adduser --shell /bin/bash tracker

RUN apt-get update && apt-get install -y \ 
python3-pip \
libpq-dev python3-dev
RUN pip3 install --upgrade pip
RUN pip install pipenv

ENV FLASK_APP=application
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src
COPY Pipfile Pipfile.lock .env .*.env /usr/src/
COPY application /usr/src/application/
COPY migrations /usr/src/migrations/
COPY scripts /usr/src/run/

RUN chmod -R +x /usr/src/run/*.sh
RUN mkdir -p /usr/src/logs/app
RUN mkdir -p /usr/src/logs/celery

RUN pipenv install --system --deploy
RUN chown -R tracker:tracker ./
USER tracker

ENTRYPOINT [ "" ]
