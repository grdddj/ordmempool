## Ordmempool

Observing the mempool in real time and notifying about new ordinals pictures.

`app.py` implements `FastAPI` server with both backend and frontend.

`Websockets` are used to notify about new ordinals.

`rsync` is used to sync the data from BTC node server to the webserver.
