# fcstverif/src/utils/logging_utils.py
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

ROOT_NAME = "fcstverif"

def init_logger(logfile: Optional[str]=None,
                level: int = logging.INFO,
                rotate: bool = True,
                max_bytes: int = 50*1024*1024,
                backup_count: int = 5) -> logging.Logger:
    logger = logging.getLogger("fcstverif")
    logger.setLevel(level)

    if logfile:
        logfile = os.path.abspath(logfile)

    # 동일 파일 핸들러가 이미 있으면 재설정하지 않음
    for h in logger.handlers:
        if isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == logfile:
            return logger

    has_stream = any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    formatter = logging.Formatter(fmt)

    # 서브프로세스인 경우 파일 핸들러 생성 건너뛰기
    is_subproc = os.environ.get("FCSTVERIF_SUBPROCESS") == "1"

    if logfile and not is_subproc:
        os.makedirs(os.path.dirname(logfile), exist_ok=True)
        if rotate:
            fh = RotatingFileHandler(logfile, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
        else:
            fh = logging.FileHandler(logfile, encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    # 스트림 핸들러는 항상(최소 하나) 유지
    if not has_stream:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(formatter)
        logger.addHandler(sh)

    return logger


def get_logger(name: str = ROOT_NAME):
    return logging.getLogger(name)