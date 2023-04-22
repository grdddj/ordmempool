#!/bin/bash

inotifywait -m -r -e create,modify,delete --format '%w%f' "${LOCAL_DIR}" | while read file
do
  echo "Change detected in ${file}, syncing..."
  rsync -avz -e "ssh -p ${PORT}" --delete "${LOCAL_DIR}/" "${REMOTE_USER}@${REMOTE_SERVER}:${REMOTE_DIR}/"
done
