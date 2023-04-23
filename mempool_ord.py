import json
import logging
import sys
import threading
import time
from decimal import Decimal
from pathlib import Path

from common import InscriptionContent, OrdinalTx, RawProxy, rpc_connection
from mempool_listen import yield_new_txs


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


def main_listening():
    conn = rpc_connection()
    for index, tx in enumerate(yield_new_txs()):
        if index % 100 == 0:
            logger.info(f"index - {index} - {tx.tx_id}")
        # if tx.block is not None:
        #     logger.warning(f"Tx is already in block! {tx.tx_id}")
        inscription = tx.get_inscription(conn)
        if inscription is None:
            continue
        if not inscription.content_type.startswith("image"):
            # logger.info(f"Ord is not an image - {tx.tx_id} - {inscription.content_type}")
            continue
        processing_thread = threading.Thread(
            target=do_process_ordinal, args=(inscription, tx, conn)
        )
        logger.info(f"Starting processing_thread for {tx.tx_id}")
        processing_thread.start()


def do_process_ordinal(
    inscription: InscriptionContent, tx: OrdinalTx, conn: RawProxy
) -> None:
    while True:
        try:
            process_ordinal(inscription, tx, conn)
            break
        except Exception as e:
            if "Broken pipe" in str(e):
                logger.error("Broken pipe")
            else:
                logger.exception(f"Exception main_listening {e}")
            conn = rpc_connection()


def process_ordinal(
    inscription: InscriptionContent, tx: OrdinalTx, conn: RawProxy
) -> None:
    logger.info(f"tx - {tx}")
    logger.info(f"inscription - {inscription}")
    file_suffix = inscription.content_type.split("/")[-1]
    if file_suffix == "svg+xml":
        file_suffix = "svg"
    file_name = f"{tx.tx_id}.{file_suffix}"
    data_file = data_dir / file_name
    json_file = data_dir / f"{file_name}.json"
    if not data_file.exists() or data_file.stat().st_size == 0:
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
    if not json_file.exists() or json_file.stat().st_size == 0:
        with open(json_file, "w") as f:
            json.dump(data, f, indent=1, cls=DecimalEncoder)
    logger.info(f"Files saved - {data_file}")


if __name__ == "__main__":
    logger.info("Starting main_listening")
    while True:
        try:
            main_listening()
        except KeyboardInterrupt:
            logger.info("Stopping...")
            sys.exit(0)
        except Exception as e:
            logger.exception(f"Exception {e}")
            logger.info("Recovering from error...")
            continue
