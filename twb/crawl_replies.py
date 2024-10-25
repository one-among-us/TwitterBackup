import argparse
import json
from pathlib import Path

from hypy_utils import printc

from twb.twitter_gql import TwitterGQL


def crawl_replies_main():
    parser = argparse.ArgumentParser("Twitter Backup Tool")
    parser.add_argument('export_dir', help='Directory containing the exported tweets')
    parser.add_argument("-c", "--cookies", help="A folder containing EditThisCookie export json files", default="cookiezi")
    args = parser.parse_args()

    # Create API
    cp = Path(args.cookies)
    if not cp.exists():
        printc('&cCookies file not found')
        return

    api = TwitterGQL(cp, base_dir=args.export_dir)

    # Read export file and parse tweet IDs
    export_dir = Path(args.export_dir) / 'data/tweets.js'
    if not export_dir.exists():
        printc('&cExport file not found')
        return

    # Read as json
    export_json = export_dir.read_text().replace('window.YTD.tweets.part0 = ', '')
    export_data = json.loads(export_json)

    # Get tweet IDs
    tweet_ids = [tweet['tweet']['id'] for tweet in export_data if tweet['tweet'].get('in_reply_to_status_id')]

    # Crawl replies
    for tweet_id in tweet_ids:
        api.crawl_parent(tweet_id)


if __name__ == '__main__':
    crawl_replies_main()
