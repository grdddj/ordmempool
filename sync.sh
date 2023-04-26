#!/bin/bash

LOCAL_DIR="/home/pi/mempool_ord/static/pictures"
# LOCAL_DIR="/home/pi/bitcoin/trial"
REMOTE_USER="jirka"
REMOTE_SERVER="89.221.219.124"
REMOTE_DIR="/home/jirka/ordmempool/static/pictures"
# REMOTE_DIR="/home/jirka/ordmempool/trial"
PORT="2020"

inotifywait -m -r -e create,modify,delete --format '%w%f' "${LOCAL_DIR}" | while read file
do
  echo "Change detected in ${file}, syncing..."
  rsync -avz -e "ssh -p ${PORT}" --delete "${LOCAL_DIR}/" "${REMOTE_USER}@${REMOTE_SERVER}:${REMOTE_DIR}/"
done
