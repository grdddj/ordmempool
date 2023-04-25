import logging
import sys
from pathlib import Path
from typing import Iterator

import zmq

from common import InscriptionContent, OrdinalTx, rpc_connection

HERE = Path(__file__).parent

zmq_context = zmq.Context()
zmq_socket = zmq_context.socket(zmq.SUB)
# zmq_topic = b"rawtx"
# zmq_socket.connect("tcp://127.0.0.1:28332")
zmq_topic = b"sequence"
zmq_socket.connect("tcp://127.0.0.1:28333")
zmq_socket.setsockopt(zmq.SUBSCRIBE, zmq_topic)
conn = rpc_connection()

log_file_path = HERE / "mempool_listen.log"
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)
log_handler = logging.FileHandler(log_file_path)
log_formatter = logging.Formatter("%(asctime)s %(message)s")
log_handler.setFormatter(log_formatter)
logger.addHandler(log_handler)


def yield_new_tx_ids() -> Iterator[str]:
    while True:
        _topic, data, _seq_num = zmq_socket.recv_multipart()
        if len(data) == 41:
            tx_id = data[:32].hex()
            added_or_deleted = chr(data[32])  # "A" or "R"
            logger.info(f"{tx_id} {added_or_deleted}")
            if added_or_deleted == "A":
                yield tx_id


def yield_new_txs() -> Iterator[OrdinalTx]:
    new_tx_ids_iterator = yield_new_tx_ids()
    while True:
        tx_id = next(new_tx_ids_iterator)
        tx = OrdinalTx.from_tx_id(tx_id, conn)
        if tx is not None:
            yield tx
        else:
            logger.warning(f"WARNING: tx is None. tx_id: {tx_id}")


def yield_new_ordinals() -> Iterator[tuple[OrdinalTx, InscriptionContent]]:
    tx_iterator = yield_new_txs()
    while True:
        tx = next(tx_iterator)
        inscription = tx.get_inscription(conn)
        if inscription is not None:
            yield tx, inscription


def main():
    print("Listening for new transactions...")

    tx_iterator = yield_new_txs()
    try:
        while True:
            tx = next(tx_iterator)
            print("tx", tx)
    except KeyboardInterrupt:
        print("Stopping...")
        sys.exit(0)


if __name__ == "__main__":
    main()
