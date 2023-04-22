from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Self
import logging

from bitcoin.rpc import JSONRPCError, RawProxy

HERE = Path(__file__).parent

BTC_SATOSHI = 100_000_000


def rpc_connection() -> RawProxy:
    return RawProxy(service_port=8332, btc_conf_file="mainnet.conf")


@dataclass
class InscriptionContent:
    content_type: str
    content_hash: str
    content_length: int
    payload: bytes

    def __repr__(self) -> str:
        return f"InscriptionContent(content_type={self.content_type}, content_hash={self.content_hash}, content_length={self.content_length})"


@dataclass
class BasicBlock:
    block_hash: str
    block_height: int
    timestamp: int

    @classmethod
    def from_block_hash(cls, block_hash: str, conn: RawProxy) -> Self | None:
        try:
            block = conn.getblock(block_hash)
        except JSONRPCError as e:
            logging.error(f"Exception BasicBlock::from_block_hash  {block_hash} : {e}")
            return None

        return cls(
            block_hash=block_hash,
            block_height=block["height"],
            timestamp=block["time"],
        )

    @classmethod
    def from_block_height(cls, block_height: int, conn: RawProxy) -> Self | None:
        try:
            block_hash = conn.getblockhash(block_height)
            block = conn.getblock(block_hash)
        except JSONRPCError as e:
            logging.error(
                f"Exception BasicBlock::from_block_height  {block_height} : {e}"
            )
            return None
        return cls(
            block_hash=block_hash,
            block_height=block_height,
            timestamp=block["time"],
        )

    @classmethod
    def from_tx_id(cls, tx_id: str, conn: RawProxy) -> Self | None:
        try:
            raw_tx = conn.getrawtransaction(tx_id, True)
            block_hash = raw_tx["blockhash"]
        except JSONRPCError as e:
            logging.error(f"Exception BasicBlock::from_tx_id  {tx_id} : {e}")
            return None
        except KeyError as e:
            # There is no blockhash, so this is a mempool transaction
            logging.error(f"Exception BasicBlock::from_tx_id  {tx_id} : {e}")
            return None
        return cls.from_block_hash(block_hash, conn)

    def datetime(self) -> str:
        return datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class Input:
    _d: dict

    def __repr__(self) -> str:
        return f"Input(tx_id={self.tx_id}, vout={self.vout})"

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        return cls(d)

    @property
    def tx_id(self) -> str:
        return self._d["txid"]

    @property
    def vout(self) -> int:
        return self._d["vout"]

    @property
    def txinwitness(self) -> list[str]:
        return self._d["txinwitness"]

    def value(self, conn: RawProxy) -> int:
        prev_tx = Tx.from_tx_id(self.tx_id, conn)
        return prev_tx.vout[self.vout].value


@dataclass
class Output:
    _d: dict

    def __repr__(self) -> str:
        return f"Output(address={self.address}, value={self.value})"

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        return cls(d)

    @property
    def address(self) -> str:
        return self._d.get("scriptPubKey", {}).get("address", "")

    @property
    def value(self) -> int:
        return int(BTC_SATOSHI * self._d["value"])


@dataclass
class Tx:
    tx_id: str
    block: BasicBlock | None
    size: int
    vsize: int
    vin: list[Input]
    vout: list[Output]

    @classmethod
    def from_tx_id(cls, tx_id: str, conn: RawProxy) -> Self | None:
        try:
            raw_tx = conn.getrawtransaction(tx_id)
        except JSONRPCError as e:
            logging.error(f"Exception Tx::from_tx_id  {tx_id} : {e}")
            return None

        return cls.from_raw_tx_data(raw_tx, conn)

    @classmethod
    def from_raw_tx_data(cls, raw_tx: str, conn: RawProxy) -> Self | None:
        try:
            tx = conn.decoderawtransaction(raw_tx)
        except JSONRPCError as e:
            logging.error(f"Exception Tx::from_raw_tx_data  {raw_tx} : {e}")
            return None

        return cls(
            tx_id=tx["txid"],
            block=BasicBlock.from_tx_id(tx["txid"], conn),
            size=tx["size"],
            vsize=tx["vsize"],
            vin=[Input.from_dict(vin) for vin in tx["vin"]],
            vout=[Output.from_dict(vout) for vout in tx["vout"]],
        )

    def fee(self, conn: RawProxy) -> int:
        return self.total_input(conn) - self.total_output()

    def fee_rate(self, conn: RawProxy) -> float:
        return self.fee(conn) / self.vsize

    def total_input(self, conn: RawProxy) -> int:
        total_input = 0
        for vin in self.vin:
            input_tx = Tx.from_tx_id(vin.tx_id, conn)
            total_input += input_tx.vout[vin.vout].value
        return total_input

    def total_output(self) -> int:
        return sum([vout.value for vout in self.vout])

    def to_dict_without_witness(self, conn: RawProxy) -> dict:
        res = asdict(self, dict_factory=dict)
        res["fee"] = self.fee(conn)
        res["fee_rate"] = self.fee_rate(conn)
        res["total_input"] = self.total_input(conn)
        res["total_output"] = self.total_output()
        for vin in res["vin"]:
            vin["_d"].pop("txinwitness")
        return res


@dataclass
class OrdinalTx(Tx):
    def get_inscription(self, conn: RawProxy) -> InscriptionContent | None:
        try:
            witness_script = self.vin[0].txinwitness[1]

            decoded_script = conn.decodescript(witness_script)["asm"]

            script_parts = decoded_script.split(" ")

            assert len(script_parts[0]) == 64, "first part is not 64"
            assert script_parts[-1] == "OP_ENDIF", "no OP_ENDIF"
            assert script_parts[1] == "OP_CHECKSIG", "no OP_CHECKSIG"

            while script_parts[2] != "0" and script_parts[3] != "OP_IF":
                # There could be some additional things, like
                # ['756e69736174', 'aeb98c9e8601', 'OP_2DROP']
                script_parts.pop(2)
            assert script_parts[2] == "0", "no 2"
            assert script_parts[3] == "OP_IF", "no OP_IF"

            assert script_parts[4] == "6582895", "no 6582895"

            while script_parts[5] != "1":
                # ['756e69736174', '6e83979d8601']
                script_parts.pop(5)
            assert script_parts[5] == "1", "no 5"

            content_type = script_parts[6]
            content_type_ascii = bytes.fromhex(content_type).decode("ascii")
            assert script_parts[7] == "0", "no 7"

            # cleanup
            if script_parts[-2] == "-2":
                script_parts.pop(-2)

            data_parts = script_parts[8:-1]
            hex_data = "".join(data_parts)

            content_length = len(hex_data) // 2

            try:
                payload = bytes.fromhex(hex_data)
            except ValueError:
                first_index = len(witness_script) - (content_length * 2) - 2
                data = witness_script[first_index:-2]
                payload = bytes.fromhex(data)

            return InscriptionContent(
                content_length=content_length,
                content_type=content_type_ascii,
                content_hash=hashlib.md5(payload).hexdigest(),
                payload=payload,
            )
        except AssertionError as e:
            logging.error(f"AssertionError {self.tx_id} : {e}")
            return None
        except Exception as e:
            logging.error(f"Exception {self.tx_id} : {e}")
            return None
