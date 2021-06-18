# PetitionTrackerUK


### [PetitionTrackerUK](https://petitiontracker.co.uk/ "PetitionTrackerUK Homepage link") enables the tracking and visualisation of UK petitions by country, region and constituency.


## Components
---
- React & Chart.js UI
- Flask REST API (`/api`)
- EFK logging stack
- PSQL/SQLalchemy ORM
- PSQL/Celery/Redbeat Tasks + Scheduler

## Installation
---

The project is designed to be run in docker containers. You can either build the docker images yourself with the relevant Dockerfiles found in `deploy/docker/build` or
alternatively you can use the public dockerhub images specified in the enviroment file at `deploy/env/.env`

docker-compose files can be found at `deploy/docker/compose`. A complete docker-compose file can be found
at the directory root and service grouped docker-compose.override.yml files within the relevant subdirectories. docker images are specified using the automatically loaded docker-compose `.env` file. If using postgres within a docker container specify the configuration using `.postgres.env`

The flask_api and celery worker containers use a mounted volume to access entrypoint scripts, enviroment
variables and the task schedule. by default this is mapped as: `./mnt:/usr/src/mnt` but can be changed using the relevant enviroment variable and compose volume mounting

The core project can be brought up by running:

```bash
docker-compose up -d flask_api react_ui beat_scheduler tracker_worker redis postgres
```

scheduled tasks can be configured using a ```schedule.json``` file, examples of which can be found at ```application/lib/celery/schedule``` (see the task section for further details)
