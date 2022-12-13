from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import toml
from hypy_utils import printc


@dataclass
class Config:
    """
    Secrets configuration for this program.

    Attributes:
        - consumer_key: The consumer key from the Twitter application portal
        - consumer_secret: The consumer secret from the Twitter application portal
        - access_token: The access token of an app from the Twitter application portal
        - access_secret: The access secret of an app from the Twitter application portal

    Representation Invariants:
        - self.consumer_key != ''
        - self.consumer_secret != ''
        - self.access_token != ''
        - self.access_secret != ''
    """
    # Twitter's official API v1 keys
    consumer_key: str
    consumer_secret: str
    access_token: str
    access_secret: str


def load_config(path: str = 'config.toml') -> Config:
    """
    Load config using JSON5, from either the local file ~/config.json5 or from the environment
    variable named config.

    :param path: Path of the config file (Default: config.json5)
    :return: Config object
    """
    fp = os.getenv('twb_config_path')

    if fp is None or not os.path.isfile(fp):
        fp = path
    if fp is None or not os.path.isfile(fp):
        fp = Path.home() / ".config" / "twb" / "config.toml"

    fp = Path(fp)

    if not fp.is_file():
        printc(f"&cConfig file not found in either {path} or {fp} \nPlease put your configuration in the path")
        exit(3)

    return Config(**toml.loads(fp.read_text()))
