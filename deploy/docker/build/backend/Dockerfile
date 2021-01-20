FROM ubuntu:20.04 as APP-BASE
LABEL project=PetitionTrackerUk

ARG DEBIAN_FRONTEND="noninteractive"

RUN adduser --shell /bin/bash tracker

ENV LANG="C.UTF-8" \
    TZ=Europe/London \
    LC_ALL="C.UTF-8" \
    PATH="/opt/pyenv/shims:/opt/pyenv/bin:$PATH" \
    PYENV_ROOT="/opt/pyenv" \
    PYENV_SHELL="bash"

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo ${TZ} > /etc/timezone

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential ca-certificates python-greenlet\
    gcc make python3-dev libffi-dev pkg-config \
    libpq-dev netbase net-tools curl wget git nano\
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN git clone -b \
    v1.2.20 --single-branch --depth 1 \
    https://github.com/pyenv/pyenv.git $PYENV_ROOT && \
    pyenv install pypy3.6-7.2.0 && \
    pyenv global pypy3.6-7.2.0 && \
    pip3 install --upgrade pip && \
    pip install pipenv


FROM APP-BASE as FILE-SYS
ENV FLASK_APP=application \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /usr/src
COPY Pipfile Pipfile.lock .env /usr/src/
COPY application /usr/src/application/
COPY migrations /usr/src/migrations/

FROM FILE-SYS as DEPLOY
RUN pipenv install \
    --system \
    --deploy \
    --python pypy3.6-7.2.0 && \
    chown -R tracker:tracker ./

USER tracker

ENTRYPOINT [ "" ]
