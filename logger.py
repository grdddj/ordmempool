from __future__ import annotations

import logging
from pathlib import Path


def get_logger(name: str, log_file_path: str | Path) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    log_handler = logging.FileHandler(log_file_path)
    log_formatter = logging.Formatter("%(asctime)s %(message)s")
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)
    return logger
