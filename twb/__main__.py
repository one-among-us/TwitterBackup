from __future__ import annotations

import argparse
from pathlib import Path

from hypy_utils import printc

from twb.twitter_gql import TwitterGQL
from .collect import download_media


def run():
    parser = argparse.ArgumentParser("Twitter Backup Tool")
    parser.add_argument("username", help="@user of the user you want to back up")
    parser.add_argument("-p", "--path", help="Output path")
    parser.add_argument("-c", "--cookies", help="A folder containing EditThisCookie export json files", default="cookiezi")
    parser.add_argument("-m", "--multithread", help="Use multithreading when downloading media (breaks progress bar)",
                        action='store_true')
    args = parser.parse_args()

    # Create API
    cp = Path(args.cookies)
    if not cp.exists():
        printc('&cCookies file not found')
        return

    api = TwitterGQL(cp)

    # Convert path
    basedir = Path(args.path or "backups")
    json_path = basedir / args.username / 'tweets.json'

    # Crawl tweets
    api.crawl_all(args.username)

    # Download media
    download_media(json_path, mt=args.multithread)

    printc('&a⭐️ All done!')


if __name__ == '__main__':
    run()
