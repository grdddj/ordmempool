from pathlib import Path

import paramiko
from scp import SCPClient

from config import Config


def send_files_to_server(*files: str | Path) -> None:
    private_key = paramiko.RSAKey.from_private_key_file(Config.private_key_file)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(Config.hostname, port=Config.port, username=Config.username, pkey=private_key)

    with SCPClient(ssh.get_transport()) as scp:
        for file in files:
            scp.put(file, Config.server_dir)

    ssh.close()
