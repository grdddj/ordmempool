from __future__ import annotations

import atexit
from pathlib import Path

import paramiko
from scp import SCPClient

from config import Config

private_key = paramiko.RSAKey.from_private_key_file(Config.private_key_file)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(
    Config.hostname, port=Config.port, username=Config.username, pkey=private_key
)
scp_client = SCPClient(ssh.get_transport())


def close_ssh() -> None:
    print("closing ssh")
    ssh.close()


def close_scp() -> None:
    print("closing scp")
    scp_client.close()


def send_files_to_server(*files: str | Path) -> None:
    for file in files:
        scp_client.put(file, Config.server_dir)


atexit.register(close_scp)
atexit.register(close_ssh)
