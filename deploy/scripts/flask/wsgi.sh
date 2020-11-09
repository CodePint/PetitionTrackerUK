#!/bin/bash

echo Starting Gunicorn WSGI!
exec pipenv run gunicorn -b :5000 \
    --access-logfile -\
    --error-logfile -\
    --capture-output \
    --enable-stdio-inheritance \
    --log-level debug \
    application.wsgi:app