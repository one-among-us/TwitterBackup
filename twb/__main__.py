from __future__ import annotations

import argparse
from pathlib import Path

from hypy_utils import printc

from .chain import chain_exp, chain_dl, chain_media
from .collect import tweepy_login, download_all_tweets, download_media
from .config import load_config


def run():
    parser = argparse.ArgumentParser("Twitter Backup Tool")
    parser.add_argument("username", help="@user of the user you want to back up")
    parser.add_argument("-p", "--path", help="Output path")
    parser.add_argument("-c", "--config", help="Config file path")
    parser.add_argument("-m", "--multithread", help="Use multithreading when downloading media (breaks progress bar)",
                        action='store_true')
    parser.add_argument("--chain-dl", help="Download all tweets for people in filtered friend chain",
                        action='store_true')
    parser.add_argument("--chain-exp", help="Expand friend chain user list",
                        action='store_true')
    parser.add_argument("--chain-media", help="Download all media from downloaded users",
                        action='store_true')
    args = parser.parse_args()

    # Load config
    config = load_config(args.config or "config.toml")

    # Login
    api = tweepy_login(config)

    # Convert path
    BASEDIR = Path(args.path or "backups")
    json_path = BASEDIR / args.username / 'tweets.json'

    if args.chain_exp:
        chain_exp(api)
        exit(0)
    if args.chain_dl:
        chain_dl(api)
        exit(0)
    if args.chain_media:
        chain_media()
        exit(0)

    # Crawl tweets
    download_all_tweets(api, args.username, json_path)

    # Download media
    download_media(json_path, mt=args.multithread)

    printc('&a⭐️ All done!')


if __name__ == '__main__':
    run()
