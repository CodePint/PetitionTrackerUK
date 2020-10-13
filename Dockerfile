
FROM ubuntu:20.04
RUN adduser --shell /bin/bash tracker

RUN apt-get update && apt-get install -y \ 
python3-pip \
libpq-dev python3-dev
RUN pip3 install --upgrade pip
RUN pip install pipenv

ENV FLASK_APP=application
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PROJECT_DIR /usr/src/application

RUN mkdir -p ${PROJECT_DIR}
RUN mkdir -p /usr/src/logs/app

WORKDIR /usr/src
COPY Pipfile Pipfile.lock boot.sh .env .*.env /usr/src/
COPY migrations /usr/src/migrations/

RUN chmod +x boot.sh
RUN pipenv install --system --deploy
RUN chown -R tracker:tracker ./

USER tracker
ENTRYPOINT [ "" ]
