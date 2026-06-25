import json
import logging
import os
from datetime import datetime
from pathlib import Path


def fallback_path(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return path.with_name(f"{path.stem}_{stamp}_{os.getpid()}{path.suffix}")


def build_logger(path: Path) -> logging.Logger:
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("customer_agent")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    try:
        file_handler = logging.FileHandler(path, encoding="utf-8")
    except OSError:
        alt = fallback_path(path)
        file_handler = logging.FileHandler(alt, encoding="utf-8")
        logger.warning("Primary log file %s is not writable; using %s.", path, alt)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    for target in (path, fallback_path(path)):
        try:
            with target.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            return
        except OSError:
            continue
