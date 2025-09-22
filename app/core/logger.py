import logging
import sys
import os

def setup_logger():
    if not os.path.exists("logs"):
        os.makedirs("logs")

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    info_handler = logging.FileHandler("logs/info.log")
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)
    logger.addHandler(info_handler)

    warning_handler = logging.FileHandler("logs/warning.log")
    warning_handler.setLevel(logging.WARNING)
    warning_handler.setFormatter(formatter)
    logger.addHandler(warning_handler)

    error_handler = logging.FileHandler("logs/error.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

def get_vehicle_logger(license_plate_number):
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger(license_plate_number)
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    log_file = os.path.join(log_dir, f"{license_plate_number}.log")
    handler = logging.FileHandler(log_file)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
