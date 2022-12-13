from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import toml


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
    path = Path(os.getenv('twb_config_path') or path)

    assert path.is_file(), f"Config file not found: {path.absolute()}. \nPlease put your configuration in the path"

    return Config(**toml.loads(path.read_text()))
