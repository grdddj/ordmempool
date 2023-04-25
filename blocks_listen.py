from __future__ import annotations

from typing import Iterator
import logging
from pathlib import Path
import time

import zmq

from common import rpc_connection

HERE = Path(__file__).parent

PICS_DIR = HERE / "mempool_data" / "static" / "pictures"

zmq_context = zmq.Context()
zmq_socket = zmq_context.socket(zmq.SUB)
zmq_topic = b"hashblock"
zmq_socket.connect("tcp://127.0.0.1:28334")
zmq_socket.setsockopt(zmq.SUBSCRIBE, zmq_topic)
conn = rpc_connection()

log_file_path = HERE / "blocks_listen.log"
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)
log_handler = logging.FileHandler(log_file_path)
log_formatter = logging.Formatter("%(asctime)s %(message)s")
log_handler.setFormatter(log_formatter)
logger.addHandler(log_handler)


def yield_new_block_hashes() -> Iterator[str]:
    while True:
        _topic, block_hash, _seq_num = zmq_socket.recv_multipart()
        block_hash_str = block_hash.hex()
        yield block_hash_str


def yield_tx_ids_from_new_blocks() -> Iterator[str]:
    block_iter = yield_new_block_hashes()
    while True:
        block_hash = next(block_iter)
        for tx_id in conn.getblock(block_hash)["tx"]:
            yield tx_id


def delete_tx_id_from_mempool_dir(tx_id: str) -> None:
    file_pattern = f"{tx_id}*"
    for file in PICS_DIR.glob(file_pattern):
        file.unlink()


def load_all_ords_in_mempool() -> set[str]:
    all_ids = [file.name.split(".")[0] for file in PICS_DIR.glob("*.json")]
    all_ids = set(all_ids)
    return all_ids


def check_all_minted_ordinals_from_mempool():
    global conn
    logger.info("Starting check_all_minted_ordinals_from_mempool")
    block_iter = yield_new_block_hashes()
    while True:
        block_hash = next(block_iter)
        logger.info(f"New block hash: {block_hash}")
        while True:
            try:
                all_mempool_ids = load_all_ords_in_mempool()
                deleted_ids = []
                for mined_tx_id in conn.getblock(block_hash)["tx"]:
                    if mined_tx_id in all_mempool_ids:
                        delete_tx_id_from_mempool_dir(mined_tx_id)
                        deleted_ids.append(mined_tx_id)
                if deleted_ids:
                    logger.info(f"Deleted {len(deleted_ids)} ids: {deleted_ids}")
            except Exception as e:
                logger.exception(f"Error: {e}")
                time.sleep(1)
                logger.info("Reconnecting...")
                conn = rpc_connection()
                continue


if __name__ == "__main__":
    while True:
        try:
            check_all_minted_ordinals_from_mempool()
        except Exception as e:
            logger.exception(f"Error: {e}")
            print("Sleeping...")
            time.sleep(1)
            print("Waking up...")
