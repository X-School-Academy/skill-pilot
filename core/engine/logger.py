import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%d/%b/%Y:%H:%M:%S %z",
)
logging.Formatter.converter = time.localtime

_logger = logging.getLogger("engine")


def log(message: str) -> None:
    _logger.info(message)


def error(message: str) -> None:
    _logger.error(message)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
