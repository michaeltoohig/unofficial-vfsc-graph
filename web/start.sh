#! /usr/bin/env sh
set -e

# If there's a prestart.sh script in the /app/app directory, run it before starting
PRE_START_PATH=/app/app/prestart.sh
echo "Checking for script in $PRE_START_PATH"
if [ -f $PRE_START_PATH ] ; then
    echo "Running script $PRE_START_PATH"
    . $PRE_START_PATH
else
    echo "There is no script $PRE_START_PATH"
fi

# Start Gunicorn
exec gunicorn --config "/app/gunicorn_conf.py" "app.main:create_app()"
