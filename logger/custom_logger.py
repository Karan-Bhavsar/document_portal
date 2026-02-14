import os
import logging
from datetime import datetime
import structlog


class CustomLogger:
    _configured = False
    _log_file_path = None

    def __init__(self, log_dir="logs"):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root
        logs_dir = os.path.join(base_dir, log_dir)
        os.makedirs(logs_dir, exist_ok=True)

        if CustomLogger._log_file_path is None:
            log_file = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"
            CustomLogger._log_file_path = os.path.join(logs_dir, log_file)

    def get_logger(self, name=__file__):
        logger_name = os.path.basename(name)

        if not CustomLogger._configured:
            # Root logger config (write to console + file)
            root = logging.getLogger()
            root.setLevel(logging.INFO)
            root.handlers.clear()

            file_handler = logging.FileHandler(CustomLogger._log_file_path, encoding="utf-8")
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(logging.Formatter("%(message)s"))

            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(logging.Formatter("%(message)s"))

            root.addHandler(console_handler)
            root.addHandler(file_handler)

            structlog.configure(
                processors=[
                    structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
                    structlog.processors.add_log_level,
                    structlog.processors.EventRenamer(to="event"),
                    structlog.processors.JSONRenderer(),
                ],
                logger_factory=structlog.stdlib.LoggerFactory(),
                cache_logger_on_first_use=True,
            )

            # Helpful: print where logs are going
            root.info(f"[LOGGER] Writing logs to: {CustomLogger._log_file_path}")

            CustomLogger._configured = True

        return structlog.get_logger(logger_name)
