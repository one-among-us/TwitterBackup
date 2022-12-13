from __future__ import annotations

import argparse
from pathlib import Path

from .collect import tweepy_login, download_all_tweets, download_media
from .config import load_config


def run():
    parser = argparse.ArgumentParser("Twitter Backup Tool")
    parser.add_argument("username", help="@user of the user you want to back up")
    parser.add_argument("-p", "--path", help="Output path")
    parser.add_argument("-c", "--config", help="Config file path")
    args = parser.parse_args()

    # Load config
    config = load_config(args.config or "config.toml")

    # Login
    api = tweepy_login(config)

    # Convert path
    BASEDIR = Path(args.path or "backups")

    # Crawl tweets
    download_all_tweets(api, args.username)

    # Download media
    download_media(BASEDIR / args.username / 'tweets.json')


if __name__ == '__main__':
    run()
