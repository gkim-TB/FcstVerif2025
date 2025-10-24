# fcstverif/src/utils/logging_utils.py
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

ROOT_NAME = "fcstverif"

def init_logger(logfile: str = None,
                level: int = logging.INFO,
                rotate: bool = False,
                max_bytes: int = 20*1024*1024,
                backup_count: int = 5,
                add_stream: bool = True):
    """
    Call once per process (in main). Returns configured logger.
    """
    logger = logging.getLogger(ROOT_NAME)
    logger.setLevel(level)

    # Prevent adding handlers multiple times
    if logger.handlers:
        # update level if called again
        logger.setLevel(level)
        return logger

    formatter = logging.Formatter("[%(levelname)s][%(asctime)s] %(message)s",
                                  datefmt="%Y-%m-%d %H:%M:%S")

    if logfile:
        os.makedirs(os.path.dirname(logfile), exist_ok=True)
        if rotate:
            fh = RotatingFileHandler(logfile, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
        else:
            fh = logging.FileHandler(logfile, encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    if add_stream:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(formatter)
        logger.addHandler(sh)

    return logger

def get_logger(name: str = ROOT_NAME):
    return logging.getLogger(name)