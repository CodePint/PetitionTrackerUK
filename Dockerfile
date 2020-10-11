
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y \ 
python3-pip \
libpq-dev python3-dev

RUN pip3 install --upgrade pip
RUN pip install pipenv

ENV PROJECT_DIR /usr/src/application
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN mkdir -p ${PROJECT_DIR}
RUN mkdir -p /usr/src/logs/app

WORKDIR /usr/src
COPY Pipfile Pipfile.lock .env .env.* /usr/src/
COPY migrations /usr/src/migrations/
COPY scripts /usr/src
RUN chmod -R +X /usr/src/*.sh

RUN pipenv install --system --deploy

ENTRYPOINT [ "flask" ]
CMD ["run", "--host=0.0.0.0", "--port=5000"]