# Deployed by:
# uvicorn app:app --reload --host 0.0.0.0 --port 9001

from __future__ import annotations

from fastapi import FastAPI, Request, WebSocket  # type: ignore
from fastapi.responses import HTMLResponse, JSONResponse  # type: ignore
from fastapi.staticfiles import StaticFiles  # type: ignore
from pathlib import Path
from operator import itemgetter
import json
import logging
import asyncio

HERE = Path(__file__).parent

log_file_path = HERE / "app.log"
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)
log_handler = logging.FileHandler(log_file_path)
log_formatter = logging.Formatter("%(asctime)s %(message)s")
log_handler.setFormatter(log_formatter)
logger.addHandler(log_handler)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
pictures_path = Path("static/pictures")

connected_clients = set()

RESULT_NUM = 20


def get_client_ip(request: Request) -> str:
    if request.client is None:
        return "ghost"
    return request.client.host


@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    logger.info(f"index.html - HOST: {get_client_ip(request)}")
    index_html = Path("templates/index.html").read_text()
    return index_html


async def start_check_for_new_images():
    loop = asyncio.get_event_loop()
    loop.create_task(check_for_new_images())


async def check_for_new_images():
    latest_images = latest_images_list(num=1)
    if latest_images:
        last_creation_time = latest_images[0][1]
    else:
        last_creation_time = 0

    while True:
        new_images = latest_images_list(newer_than=last_creation_time)
        if new_images:
            last_creation_time = new_images[0][1]
            logger.info(f"Sending new images - {len(new_images)}, {last_creation_time}")
            result = add_json_data_to_images(new_images)
            for client in connected_clients:
                await client.send_json(result)

        await asyncio.sleep(1)


def latest_images_list(num: int | None = None, newer_than: float | None = None) -> list[tuple[str, float]]:
    if num is None and newer_than is None:
        raise ValueError("Either num or newer_than must be set")

    image_files = []

    for item in pictures_path.glob('*'):
        if item.is_file() and not item.name.endswith(".json"):
            image_files.append((item.name, item.stat().st_mtime))

    image_files.sort(key=itemgetter(1), reverse=True)
    if num is not None:
        return image_files[:num]
    elif newer_than is not None:
        return [item for item in image_files if item[1] > newer_than]
    else:
        raise RuntimeError("Should not happen")


def get_host_ip(websocket: WebSocket) -> str:
    try:
        return websocket.client[0]  # type: ignore
    except Exception as e:
        logger.error(f"Exception get_host_ip - {websocket} - {e}")
        return "unknown"


def get_connected_ips() -> list[str]:
    return [get_host_ip(client) for client in connected_clients]


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    logger.info(f"New client connected - HOST: {get_host_ip(websocket)}")
    logger.info(f"connected_clients {len(connected_clients)} - {get_connected_ips()}")
    try:
        while True:
            await websocket.receive_text()
            await websocket.send_json({"message": "Hello World"})
    finally:
        connected_clients.remove(websocket)
        logger.info(f"Client disconnected - HOST: {get_host_ip(websocket)}")
        logger.info(f"connected_clients {len(connected_clients)} - {get_connected_ips()}")


@app.get("/api/latest-images")
async def do_latest_images():
    latest_images = latest_images_list(num=RESULT_NUM)
    result = add_json_data_to_images(latest_images)

    return JSONResponse(content=result)


def add_json_data_to_images(images_paths: list[tuple[str, float]]) -> list[dict]:
    image_data = []
    for image_name, _creation_time in images_paths:
        json_file = pictures_path / f"{image_name}.json"
        if json_file.exists():
            try:
                json_data = json.loads(json_file.read_text())
            except json.decoder.JSONDecodeError as e:
                logger.error(f"JSONDecodeError - {image_name} - {e}")
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
    await start_check_for_new_images()
