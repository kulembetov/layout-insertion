import logging
import os
from functools import wraps
from logging.handlers import TimedRotatingFileHandler
from types import FunctionType

from django_app.config.settings import LOGGING_ON


def setup_logger(name=__name__, level=logging.INFO) -> logging.Logger:
    """
    Set up a logger with the given name and level.
    Creates 'logs' directory if it doesn't exist and saves logs there.
    Set handlers for console and file outputs.
    Returns a logger with the given name and level.
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    log_file: str = os.path.join(log_dir, f"{name}.log")

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = TimedRotatingFileHandler(log_file, when="midnight", backupCount=7)
    file_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger


def logs(logger: logging.Logger, *, on: bool = True):
    """
    Log decorator working with classes and functions.

    If decorated object is class:
        - view every method in class
        - check if method is decorated by 'logs'
        - set '_class_on' attribute to method

    if decorated object is function:
        - set '_is_logs_wrapper', '_method_on', '_class_on' to wrapper
        - enabled or disabled logger by 'enabled' parameter

    Also check if global variable 'LOGGING_ON' is True.
    """

    def deco(obj):
        # ============= class decorator =============
        if isinstance(obj, type):
            cls = obj
            for attr_name in dir(cls):
                attr = getattr(cls, attr_name)
                if hasattr(attr, "_is_logs_wrapper"):
                    attr._class_on = on
                elif isinstance(attr, (staticmethod, classmethod)) and hasattr(attr.__func__, "_is_logs_wrapper"):
                    attr.__func__._class_on = on
            return cls

        # ============ function decorator ============
        if isinstance(obj, FunctionType):
            func = obj

            @wraps(func)
            def wrapper(*args, **kwargs):
                method_on = getattr(wrapper, "_method_on", True)
                class_on = getattr(wrapper, "_class_on", True)
                enabled = method_on and class_on and LOGGING_ON

                """
                if enabled:
                    logger.disabled = False -> logger continue working
                else:
                    logger.disabled = True -> logger stop working
                """
                state_disabled = logger.disabled
                logger.disabled = not enabled

                try:
                    return func(*args, **kwargs)
                finally:
                    # set '.disabled' state back
                    logger.disabled = state_disabled

            wrapper._is_logs_wrapper = True
            wrapper._method_on = on
            wrapper._class_on = True
            return wrapper

        raise TypeError("'logs' can be used only with classes and functions. Other cases raise TypeError.")

    return deco


# # Example usage
# if __name__ == "__main__":
#     logger = setup_logger(__name__)
#
#     @logs(logger, on=True)
#     def foo():
#         logger.info(f"function 'foo'")
#
#     @logs(logger, on=False)
#     def bar():
#         logger.info(f"function 'bar'")
#
#     foo() # log on
#     bar() # log off
#
#     @logs(logger, on=True)
#     class Foo:
#         @logs(logger, on=True)
#         def a(self):
#             logger.info(f"method 'a'")
#
#         @logs(logger, on=False)
#         def b(self):
#             logger.info(f"method 'b'")
#
#
#     @logs(logger, on=False)
#     class Bar:
#         @logs(logger, on=True)
#         def x(self):
#             logger.info(f"method 'x'")
#
#         @logs(logger, on=False)
#         def y(self):
#             logger.info(f"method 'y'")
#
#     _foo = Foo()
#     _bar = Bar()
#
#     _foo.a() # log on
#     _foo.b() # log off
#
#     _bar.x() # log off
#     _bar.y() # log off
#
#     @logs(logger, on=True)
#     def multiple(x, y):
#          logger.info(f"x={x}, y={y}")
#          mul = x * y
#          logger.info(f"x * y = {mul}")
#          return mul
#
#     @logs(logger, on=False)
#     def volume(a, b, h):
#         sq = multiple(a, b)
#         logger.info(f"Square: {sq}")
#         vol = multiple(sq, h)
#         logger.info(f"Volume: {vol}")
#         return vol
#
#     v = volume(1, 2, 3)
#     logger.info(f"[FINAL LOG] Volume: {v}")
#
#     del logger, foo, bar, Foo, Bar, _foo, _bar, multiple, volume, v
