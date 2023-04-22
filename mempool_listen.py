import sys
from typing import Iterator

import zmq

from common import InscriptionContent, OrdinalTx, rpc_connection

zmq_context = zmq.Context()
zmq_socket = zmq_context.socket(zmq.SUB)
zmq_topic = b"rawtx"
zmq_socket.connect("tcp://127.0.0.1:28332")
zmq_socket.setsockopt(zmq.SUBSCRIBE, zmq_topic)
conn = rpc_connection()


def yield_new_txs() -> Iterator[OrdinalTx]:
    while True:
        _topic, raw_tx_data, _seq_num = zmq_socket.recv_multipart()
        tx = OrdinalTx.from_raw_tx_data(raw_tx_data.hex(), conn)
        if tx is not None:
            yield tx


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
