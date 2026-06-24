import json
import logging
import os
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path


class JsonLogger:
    """JSON logger class"""

    @classmethod
    def setup_logger(
        cls,
        name: str = "ember",
        log_path: Path = Path(__file__).parents[3] / "data/logs",
        log_level: int = logging.INFO,
        file_log: bool = True,
    ) -> logging.Logger:
        """Initialize the JSON logger

        Args:
            name (str): Name of the logger.
            log_level (int): The desired logging level.
            file_log (bool): If True RotatingFileHandler will serve, else StreamHandler.
        """
        os.makedirs(log_path, exist_ok=True)
        cls.name = name
        cls.log_path = log_path
        cls.logger = logging.getLogger(cls.name)
        cls.logger.setLevel(log_level)
        existing_handlers = [h for h in cls.logger.handlers]
        if not existing_handlers:
            if file_log:
                cls._setup_file_handler()
            else:
                cls._setup_stream_handler()

        return cls.logger

    @classmethod
    def _setup_file_handler(cls) -> None:
        """Configures the stream handler specifically attached to the logger instance."""
        if not any(isinstance(h, RotatingFileHandler) for h in cls.logger.handlers):
            handler = RotatingFileHandler(
                f"{cls.log_path}/{cls.name}.log", maxBytes=10000000
            )
            formatter = cls.JsonFormatter()
            handler.setFormatter(formatter)
            cls.logger.addHandler(handler)

    @classmethod
    def _setup_stream_handler(cls) -> None:
        """Configures the stream handler specifically attached to the logger instance."""
        if not any(isinstance(h, logging.StreamHandler) for h in cls.logger.handlers):
            handler = logging.StreamHandler()
            formatter = cls.JsonFormatter()
            handler.setFormatter(formatter)
            cls.logger.addHandler(handler)

    class JsonFormatter(logging.Formatter):
        """Formatter to dump log messages into JSON."""

        session_id = str(uuid.uuid4())[:8]

        def format(
            self,
            record: logging.LogRecord,
        ) -> str:
            record_dict = {
                "date": self.formatTime(record, "%d/%m/%Y %H:%M:%S"),
                "level": record.levelname,
                "session_id": self.session_id,
                "module": record.module,
                "lineno": record.lineno,
                "message": record.getMessage(),
            }
            return json.dumps(record_dict)
