#!/bin/bash

# Check if we're monitoring our own container by looking at hostname
HOSTNAME=$(hostname)
IS_BACKEND=false

if [[ "$HOSTNAME" == *"backend"* ]] || [[ "$HOSTNAME" == *"api"* ]]; then
    IS_BACKEND=true
fi

# Common uvicorn options
UVICORN_OPTS="--host 0.0.0.0 --port 8000 --reload --loop asyncio --ws-ping-interval 30 --ws-ping-timeout 10"

if [ "$IS_BACKEND" = true ]; then
    echo "Running in backend container - disabling access logs to prevent loops"
    # Disable access logs when running in backend container
    exec uvicorn app.main:app $UVICORN_OPTS --access-log=false
else
    # Normal startup with access logs
    exec uvicorn app.main:app $UVICORN_OPTS
fi