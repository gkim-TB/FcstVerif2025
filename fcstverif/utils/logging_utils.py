# fcstverif/utils/logging_utils.py

import logging
import sys

def init_logger(name="fcstverif", level=logging.INFO):
    """
    전역 로거 초기화 함수.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:  # 중복 핸들러 방지
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "[%(levelname)s][%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
