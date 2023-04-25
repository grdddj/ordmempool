# Deployed by:
# uvicorn app:app --reload --host 0.0.0.0 --port 9001

from __future__ import annotations

import asyncio
import json
import logging
import os
from operator import itemgetter
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket  # type: ignore
from fastapi.responses import HTMLResponse, JSONResponse  # type: ignore
from fastapi.staticfiles import StaticFiles  # type: ignore
from watchdog.events import FileSystemEventHandler  # type: ignore
from watchdog.observers.polling import PollingObserver  # type: ignore

HERE = Path(__file__).parent

log_file_path = HERE / "app.log"
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)
log_handler = logging.FileHandler(log_file_path)
log_formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
log_handler.setFormatter(log_formatter)
logger.addHandler(log_handler)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
pictures_path = Path("static/pictures")

connected_clients = set()

RESULT_NUM = 20


def get_request_port(request: Request) -> int:
    return request.scope["server"][1]


def get_client_ip(request: Request) -> str:
    if request.client is None:
        return "ghost"
    return request.client.host


# So we know which instance of the app is serving the request
port = 0


@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    global port
    if port == 0:
        port = get_request_port(request)
    logger.info(f"{port} - index.html - HOST: {get_client_ip(request)}")
    index_html = Path("templates/index.html").read_text()
    return index_html


async def start_check_for_new_images(path: str):
    loop = asyncio.get_event_loop()
    loop.create_task(check_for_new_images(path))


class NewJsonFileHandler(FileSystemEventHandler):
    def on_created(self, event) -> None:
        if event.is_directory:
            return
        new_file_path = event.src_path
        file_name, file_ext = os.path.splitext(os.path.basename(new_file_path))

        if file_ext == ".json":
            # need to call async function from sync function
            asyncio.run(send_new_result_to_clients(new_file_path))

    def on_deleted(self, event):
        if event.is_directory:
            return
        new_file_path = event.src_path
        file_name, file_ext = os.path.splitext(os.path.basename(new_file_path))

        if file_ext == ".json":
            asyncio.run(send_deletions_to_clients(new_file_path))


async def send_deletions_to_clients(json_file_path: str) -> None:
    tx_id = Path(json_file_path).name.split(".")[0]
    logger.info(f"Deletion - {tx_id}")
    result = {
        "type": "tx_deleted",
        "payload": tx_id,
    }
    for client in connected_clients:
        await client.send_json(result)


async def send_new_result_to_clients(json_file_path: str) -> None:
    try:
        logger.info(f"{port} - New result - {json_file_path}")
        data = json.loads(Path(json_file_path).read_text())
        creation_time = os.path.getmtime(json_file_path)
        # image has the same name as json file, so delete .json from the end
        image = Path(json_file_path[: -len(".json")]).name
        # clients expect a list
        result = [{"image": image, "data": data, "creation_time": creation_time}]

        result = {
            "type": "new_tx",
            "payload": result,
        }

        for client in connected_clients:
            await client.send_json(result)
    except Exception as e:
        logger.exception(f"{port} - Exception send_new_result_to_clients - {e}")


async def check_for_new_images(path: str):
    event_handler = NewJsonFileHandler()
    observer = PollingObserver()  # because rsync does not trigger events
    observer.schedule(event_handler, path, recursive=False)
    observer.start()


def get_host_ip(websocket: WebSocket) -> str:
    try:
        return websocket.client[0]  # type: ignore
    except Exception as e:
        logger.error(f"{port} - Exception get_host_ip - {websocket} - {e}")
        return "unknown"


def get_connected_ips() -> list[str]:
    return [get_host_ip(client) for client in connected_clients]


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await websocket.accept()
        connected_clients.add(websocket)
        logger.info(f"{port} - New client connected - HOST: {get_host_ip(websocket)}")
        logger.info(
            f"{port} - connected_clients {len(connected_clients)} - {get_connected_ips()}"
        )
    except Exception as e:
        logger.exception(f"{port} - Exception websocket_endpoint - {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    try:
        while True:
            await websocket.receive_text()
            await websocket.send_json({"message": "Hello World"})
    finally:
        connected_clients.remove(websocket)
        logger.info(f"{port} - Client disconnected - HOST: {get_host_ip(websocket)}")
        logger.info(
            f"{port} - connected_clients {len(connected_clients)} - {get_connected_ips()}"
        )


@app.get("/api/latest-images")
async def do_latest_images(request: Request):
    try:
        logger.info(f"{port} - Latest images - HOST: {get_client_ip(request)}")
        latest_images = latest_images_list(num=RESULT_NUM)
        result = add_json_data_to_images(latest_images)

        return JSONResponse(content=result)
    except Exception as e:
        logger.exception(f"{port} - Exception do_latest_images - {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def latest_images_list(
    num: int | None = None, newer_than: float | None = None
) -> list[tuple[str, float]]:
    if num is None and newer_than is None:
        raise ValueError("Either num or newer_than must be set")

    image_files = []

    for item in pictures_path.glob("*"):
        if item.is_file() and not item.name.endswith(".json"):
            image_files.append((item.name, item.stat().st_mtime))

    image_files.sort(key=itemgetter(1), reverse=True)
    if num is not None:
        return image_files[:num]
    elif newer_than is not None:
        return [item for item in image_files if item[1] > newer_than]
    else:
        raise RuntimeError("Should not happen")


def add_json_data_to_images(images_paths: list[tuple[str, float]]) -> list[dict]:
    image_data = []
    for image_name, _creation_time in images_paths:
        json_file = pictures_path / f"{image_name}.json"
        if json_file.exists():
            try:
                json_data = json.loads(json_file.read_text())
            except json.decoder.JSONDecodeError as e:
                logger.error(f"{port} - JSONDecodeError - {image_name} - {e}")
                json_data = {}
            image_data.append(json_data)
    images_and_data = list(zip(images_paths, image_data))
    result = []
    for (image, creation_time), data in images_and_data:
        result.append({"image": image, "data": data, "creation_time": creation_time})
    return result


# Register the event handler for server startup
@app.on_event("startup")
async def on_startup():
    pictures_dir = HERE / "static" / "pictures"
    logger.info(f"Starting up - watching {pictures_dir}")
    await start_check_for_new_images(str(pictures_dir))
