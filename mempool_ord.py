import json
import sys
import threading
import time
from decimal import Decimal
from http.client import CannotSendRequest
from pathlib import Path

from common import InscriptionContent, OrdinalTx, RawProxy, rpc_connection
from logger import get_logger
from mempool_listen import yield_new_txs


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super(DecimalEncoder, self).default(obj)


HERE = Path(__file__).parent

log_file_path = HERE / "mempool_ord.log"
logger = get_logger(__file__, log_file_path)

data_dir = HERE / "static" / "pictures"

ordinals_processed = 0

conn = rpc_connection()


def main_listening():
    global conn
    for index, tx in enumerate(yield_new_txs()):
        if index % 100 == 0:
            logger.info(f"index - {index} - {tx.tx_id}")
        exception_there = False
        while True:
            try:
                inscription = tx.get_inscription(conn)
                if exception_there:
                    logger.info(f"Recovered from error {tx.tx_id}")
                break
            except CannotSendRequest:
                logger.error("Cannot send request")
            except Exception as e:
                logger.exception(f"Exception main_listening {e}")
            conn = rpc_connection()
            exception_there = True
            time.sleep(1)
        if inscription is None:
            continue
        global ordinals_processed
        ordinals_processed += 1
        if ordinals_processed % 50 == 0:
            logger.info(f"Ordinal processed - {ordinals_processed} - {tx.tx_id}")
        if not inscription.content_type.startswith("image"):
            continue
        processing_thread = threading.Thread(
            target=do_process_ordinal, args=(inscription, tx)
        )
        logger.info(f"Starting processing_thread for {tx.tx_id}")
        processing_thread.start()


def do_process_ordinal(inscription: InscriptionContent, tx: OrdinalTx) -> None:
    global conn
    exception_there = False
    while True:
        try:
            process_image_ordinal(inscription, tx, conn)
            if exception_there:
                logger.info(f"Recovered from error {tx.tx_id}")
            break
        except CannotSendRequest:
            logger.error("Cannot send request")
        except Exception as e:
            logger.exception(f"Exception main_listening {e}")
        conn = rpc_connection()
        exception_there = True
        time.sleep(1)


def process_image_ordinal(
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
            conn = rpc_connection()
            time.sleep(1)
            continue
