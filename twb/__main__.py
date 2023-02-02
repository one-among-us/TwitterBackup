from __future__ import annotations

import argparse
from pathlib import Path

from hypy_utils import printc

from .chain import test_main
from .collect import tweepy_login, download_all_tweets, download_media
from .config import load_config


def run():
    parser = argparse.ArgumentParser("Twitter Backup Tool")
    parser.add_argument("username", help="@user of the user you want to back up")
    parser.add_argument("-p", "--path", help="Output path")
    parser.add_argument("-c", "--config", help="Config file path")
    parser.add_argument("-m", "--multithread", help="Use multithreading when downloading media (breaks progress bar)",
                        action='store_true')
    parser.add_argument("-t", "--test", help="Call testing function instead",
                        action='store_true')
    args = parser.parse_args()

    # Load config
    config = load_config(args.config or "config.toml")

    # Login
    api = tweepy_login(config)

    # Convert path
    BASEDIR = Path(args.path or "backups")
    json_path = BASEDIR / args.username / 'tweets.json'

    if args.test:
        test_main(api)
        exit(0)

    # Crawl tweets
    download_all_tweets(api, args.username, json_path)

    # Download media
    download_media(json_path, mt=args.multithread)

    printc('&a⭐️ All done!')


if __name__ == '__main__':
    run()
