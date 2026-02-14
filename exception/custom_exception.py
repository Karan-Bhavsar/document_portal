import sys
import traceback

from logger.custom_logger import CustomLogger
logger = CustomLogger().get_logger(__file__)


class DocumentPortalException(Exception):
    """Base exception class for Document Portal errors."""

    def __init__(self, error_message, error_details=sys):
        # Capture traceback info
        exc_type, exc_val, exc_tb = error_details.exc_info()

        # Fix: frame attribute is f_code (not fcode)
        self.file_name = exc_tb.tb_frame.f_code.co_filename
        self.line_number = exc_tb.tb_lineno

        self.error_message = str(error_message)

        # Store full traceback string
        self.traceback_str = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))

        # Initialize base Exception properly
        super().__init__(self.error_message)

    def __str__(self):
        return f"""
Error Message: {self.error_message}
File Name: {self.file_name}
Line Number: {self.line_number}
Traceback: {self.traceback_str}
"""


if __name__ == "__main__":
    try:
        # Simulate an error
        a = 1 / 0
    except Exception as e:
        app_exc = DocumentPortalException(e, sys)
        logger.error(app_exc)
        raise app_exc from e