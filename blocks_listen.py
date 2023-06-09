from __future__ import annotations

import time
from pathlib import Path
from typing import Iterator

import zmq

from common import rpc_connection
from logger import get_logger

HERE = Path(__file__).parent

PICS_DIR = HERE / "static" / "pictures"

zmq_context = zmq.Context()
zmq_socket = zmq_context.socket(zmq.SUB)
zmq_topic = b"hashblock"
zmq_socket.connect("tcp://127.0.0.1:28334")
zmq_socket.setsockopt(zmq.SUBSCRIBE, zmq_topic)
conn = rpc_connection()

log_file_path = HERE / "blocks_listen.log"
logger = get_logger(__file__, log_file_path)


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
                logger.info(f"Ords in mempool {len(all_mempool_ids)}")
                deleted_ids = []
                all_block_tx_ids = conn.getblock(block_hash)["tx"]
                for mined_tx_id in all_block_tx_ids:
                    if mined_tx_id in all_mempool_ids:
                        delete_tx_id_from_mempool_dir(mined_tx_id)
                        deleted_ids.append(mined_tx_id)
                logger.info(f"Block had {len(all_block_tx_ids)} txs")
                logger.info(f"Deleted {len(deleted_ids)} ids: {deleted_ids}")
                break
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
