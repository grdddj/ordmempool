import json
import logging
import time
from decimal import Decimal
from pathlib import Path

from common import InscriptionContent, OrdinalTx, RawProxy, rpc_connection
from mempool_listen import yield_new_ordinals
from send_to_server import send_files_to_server


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super(DecimalEncoder, self).default(obj)


HERE = Path(__file__).parent

log_file_path = HERE / "mempool_ord.log"
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)
log_handler = logging.FileHandler(log_file_path)
log_formatter = logging.Formatter("%(asctime)s %(message)s")
log_handler.setFormatter(log_formatter)
logger.addHandler(log_handler)

data_dir = HERE / "mempool_data" / "static" / "pictures"


def main_polling():
    conn = rpc_connection()
    mempool_txs_prev = set(conn.getrawmempool())
    print("mempool_txs_prev", len(mempool_txs_prev))
    for tx_id in mempool_txs_prev:
        process_tx_id(tx_id, conn)

    while True:
        mempool_txs_current = set(conn.getrawmempool())
        new_txs = mempool_txs_current - mempool_txs_prev
        print("new_txs", len(new_txs))
        for tx_id in new_txs:
            process_tx_id(tx_id, conn)
        mempool_txs_prev = mempool_txs_current
        time.sleep(0.3)


def main_listening():
    conn = rpc_connection()
    for tx, inscription in yield_new_ordinals():
        while True:
            try:
                process_ordinal(inscription, tx, conn)
                break
            except Exception as e:
                if "Broken pipe" in str(e):
                    logger.error(f"Broken pipe")
                else:
                    logger.exception(f"Exception main_listening {e}")
                conn = rpc_connection()


def process_tx_id(tx_id: str, conn: RawProxy) -> None:
    tx = OrdinalTx.from_tx_id(tx_id, conn)
    if tx is None:
        return
    inscription = tx.get_inscription(conn)
    if inscription is None:
        return
    process_ordinal(inscription, tx, conn)


def process_ordinal(
    inscription: InscriptionContent, tx: OrdinalTx, conn: RawProxy
) -> None:
    if not inscription.content_type.startswith("image"):
        return
    logger.info(f"tx - {tx}")
    logger.info(f"inscription - {inscription}")
    file_suffix = inscription.content_type.split("/")[-1]
    file_name = f"{tx.tx_id}.{file_suffix}"
    data_file = data_dir / file_name
    json_file = data_dir / f"{file_name}.json"
    with open(data_file, "wb") as f:
        f.write(inscription.payload)
    data = tx.to_dict_without_witness(conn)
    data["content_type"] = inscription.content_type
    data["content_hash"] = inscription.content_hash
    data["content_length"] = inscription.content_length
    data["timestamp"] = int(time.time())
    data["datetime"] = time.strftime(
        "%Y-%m-%d %H:%M:%S UTC", time.gmtime(int(time.time()))
    )
    with open(json_file, "w") as f:
        json.dump(data, f, indent=1, cls=DecimalEncoder)
    send_files_to_server(data_file, json_file)
    logger.info(f"Files sent - {data_file}")


if __name__ == "__main__":
    # main_polling()
    logger.info("Starting main_listening")
    main_listening()
