from contextlib import contextmanager
import warnings

from .logging import log

class AICertException(Exception):
    """Generic AICert exception"""
    def __init__(self, message: str, *args: object) -> None:
        self.message = message
        super().__init__(self.message, *args)

@contextmanager
def log_errors_and_warnings():
    """Context manager that intercepts AICert errors and warnings and that logs them
    
    Only errors that inherit from AICertClientException are caught.
    They are used to display a nice error message before cleanly exiting the program.
    All warnings are caught and logged (and the program continues).

    Example usage:
    ```py
    with log_errors_and_warnings():
        # Potential errors are logged
        # and the program is properly terminated
        function_that_may_fail()
    ```
    """
    try:
        yield None
    except AICertException as e:
        log.error(f"{e.message}")
        exit(1)
    finally:
        with warnings.catch_warnings(record=True) as ws:
            for w in ws:
                log.warning(w.message)
