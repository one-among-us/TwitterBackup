from __future__ import annotations

import inspect

from .constants import DEBUG


def debug(msg: object) -> None:
    """
    Output a debug message, usually from another function

    :param msg: Message
    """
    if DEBUG:
        caller = inspect.stack()[1].function
        print(f'[DEBUG] {caller}: {msg}')
