# Application Config
## Enviroment files for: Application, Workers, Postgres
- ref config/env directory
- Specify the flask application and enviroment in '.env' file: (testing, developing, production)
- Place enviroment specific settings in the corresponding env file: '.test.env', '.dev.env', '.prod.env' (see context dir)
- Specify additional env files with the OVERRIDES enviroment variable i.e: OVERRIDES=[.task.env, .docker.env, .local.env] (see overrides dir)
- Postgres config should be in the corrersponding flask application .*.env file
- Copy these files into the project root before build or run (.env and .*.env are included in .gitignore)

## Docker files
- ref config/docker directory
- docker-compose.yml holds the base config and references the application/frontend dockerfiles
- docker-compose.override.yml holds any additional enviroment specific configuration (i.e volumes or env_file)
- .prod.yml/dev.yml hold example configurations for dev/prod which can be copied to .override.yml
- copy .override.yml to the project root in order for dockker-compose build/run to pick up the changes (also on .gitignore)

## Deployment
- ref config/deploy directory
- deploy/docker-compose.yml is used in production and will read the enviroment variables from .env
- the compose files uses enviroment variables to specify which docker image tag to use
- the base project can be run with docker-compose up -d
- additional celery workers can be spun up with the create_worker.sh script

## Tasks
- the task schedule can be found in tasks/schedule.json, included is an example config
- copy deploy.json file into application/lib/celery/tasks/schedule/schedule.json
- these tasks can be then loaded into the database by running CeleryUtils.init_schedule() or custom flask cli