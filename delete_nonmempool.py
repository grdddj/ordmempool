from pathlib import Path

from common import rpc_connection

HERE = Path(__file__).parent

PICS_DIR = HERE / "static" / "pictures"


def load_all_ords_in_mempool() -> set[str]:
    all_ids = [file.name.split(".")[0] for file in PICS_DIR.glob("*.json")]
    all_ids = set(all_ids)
    return all_ids


def delete_tx_id_from_mempool_dir(tx_id: str) -> None:
    file_pattern = f"{tx_id}*"
    for file in PICS_DIR.glob(file_pattern):
        file.unlink()


conn = rpc_connection()

all_mempool_txs = conn.getrawmempool(True)
print("all_mempool_txs", len(all_mempool_txs))

all_tx_ids_in_ = load_all_ords_in_mempool()
print("There", len(all_tx_ids_in_))

missing = []
for mempool_tx_id in all_tx_ids_in_:
    if mempool_tx_id not in all_mempool_txs:
        missing.append(mempool_tx_id)

print("missing", len(missing))

for tx_id in missing:
    delete_tx_id_from_mempool_dir(tx_id)
