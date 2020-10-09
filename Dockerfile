
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y \ 
python3-pip \
libpq-dev python3-dev

RUN pip3 install --upgrade pip
RUN pip install pipenv

ENV PROJECT_DIR /usr/src/application
RUN mkdir -p ${PROJECT_DIR}
RUN mkdir -p /usr/src/logs/app

WORKDIR /usr/src
COPY Pipfile Pipfile.lock .env .prod.env .dev.env .docker.dev.env /usr/src/
COPY migrations /usr/src/migrations/
RUN pipenv install --system --deploy

ENTRYPOINT [ "flask" ]
CMD ["run", "--host=0.0.0.0", "--port=5000"]