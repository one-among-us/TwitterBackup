from __future__ import annotations

import json
import time
from pathlib import Path

import hypy_utils.downloader
from hypy_utils import write, json_stringify, printc, ensure_dir
from tweepy import API, Tweet, Unauthorized, NotFound, OAuthHandler, User

from .config import Config
from .utils import debug


def tweepy_login(conf: Config) -> API:
    """
    Login to tweepy

    :param conf: Config from load_config()
    :return: Tweepy API object
    """
    auth = OAuthHandler(conf.consumer_key, conf.consumer_secret)
    auth.set_access_token(conf.access_token, conf.access_secret)
    api: API = API(auth)
    try:
        login: User = api.verify_credentials()
        printc(f"&aLogin success! Logged in as {login.name}")
    except Unauthorized:
        printc("&cLogin failed: Unauthorized 😭\n"
               "&rPlease verify if these tokens are correct:\n"
               f"{json_stringify(conf, indent=2)}")
        exit(12)
    return api


def calculate_rate_delay(rate_limit: float) -> float:
    """
    Calculate the rate delay for each request given rate limit in request per minute

    :param rate_limit: Rate limit in requests per minute
    :return: Rate delay in seconds per request
    """
    return 1 / rate_limit * 60


def get_tweets(api: API, name: str, rate_delay: float, max_id: int | None) -> list[Tweet]:
    """
    Get tweets and wait for delay

    :param api: Tweepy API object
    :param name: Screen name
    :param rate_delay: Seconds of delay per request
    :param max_id: Max id of the tweet or none
    :return: Tweets list
    """
    tweets = api.user_timeline(screen_name=name, count=200, tweet_mode='extended', trim_user=True,
                               max_id=max_id)
    time.sleep(rate_delay)
    return tweets


def download_all_tweets(api: API, screen_name: str,
                        download_if_exists: bool = False) -> None:
    """
    Download all tweets from a specific individual to a local folder.

    Data Directory
    --------
    It will download all tweets to ./data/twitter/user-tweets/user/<screen_name>.json

    Twitter API Reference
    --------
    It will be using the API endpoint api.twitter.com/statuses/user_timeline (Documentation:
    https://developer.twitter.com/en/docs/twitter-api/v1/tweets/timelines/api-reference/get
    -statuses-user_timeline)
    This endpoint has a rate limit of 900 requests / 15-minutes = 60 rpm for user auth, and it has a
    limit of 100,000 requests / 24 hours = 69.44 rpm independent of authentication method. To be
    safe, this function uses a rate limit of 60 rpm.

    :param api: Tweepy API object
    :param screen_name: Screen name of that individual
    :param download_if_exists: Whether to download if it already exists (Default: False)
    :return: None
    """
    # Ensure directories exist
    file = BASEDIR / screen_name / 'tweets.json'

    # Check if user already exists
    if file.is_file():
        if download_if_exists:
            debug(f'!!! User tweets data for {screen_name} already exists, but overwriting.')
        else:
            debug(f'User tweets data for {screen_name} already exists, skipping.')
            return

    debug(f'Downloading user tweets for {screen_name}')

    # Rate limit for this endpoint is 60 rpm for user auth and 69.44 rpm for app auth.
    rate_delay = calculate_rate_delay(60)

    # Get initial 200 tweets
    try:
        tweets = get_tweets(api, screen_name, rate_delay, None)
    except Unauthorized:
        debug(f'- {screen_name}: Unauthorized. Probably a private account, ignoring.')
        return
    except NotFound:
        debug(f'- {screen_name}: Not found. Probably a deleted account, ignoring.')
        return

    # This person has no tweets, done. (By the way, we discovered that @lorde has no tweets but has
    # 7 million followers... wow!)
    if len(tweets) == 0:
        write(file, '[]')
        return

    # Get additional tweets
    while True:
        # Try to get more tweets
        debug(f'- {screen_name}: {len(tweets)} tweets...')
        additional_tweets = get_tweets(api, screen_name, rate_delay, int(tweets[-1].id_str) - 1)

        # No more tweets
        if len(additional_tweets) == 0:
            debug(f'- {screen_name}: {len(tweets)} tweets, no more tweets are available.\n')
            break

        # Add tweets to the list
        tweets.extend(additional_tweets)

    # Store in file
    # Even though we are not supposed to use internal fields, there aren't any efficient way of
    # obtaining the json without the field. Using t.__dict__ will include the API object, which
    # is not serializable.
    write(file, json_stringify([t._json for t in tweets], indent=2))


def download_media(json_path: Path):
    """
    Download media urls embedded in a twitter json to somewhere local

    :param json_path: Path to tweets.json
    """
    dp = json_path.parent
    obj = json.loads(json_path.read_text())

    def download(media: dict):
        url: str = media['media_url_https']
        fp = ensure_dir(dp / 'media') / url.split("/")[-1]
        hypy_utils.downloader.download_file(url, fp)
        media['local_media_path'] = str(fp.relative_to(dp))

        # For videos
        if media['type'] == 'video':
            # Find video URL of the video with the highest bitrate
            v = max(media['video_info']['variants'], key=lambda x: x.get('bitrate') or 0)
            print(f"Downloading video {v}")
            url = v['url']
            fp = ensure_dir(dp / 'media' / 'video') / url.split("/")[-1].split("?")[0]
            # check_call(["youtube-dl", url, '-o', fp])
            hypy_utils.downloader.download_file(url, fp)
            media['local_video_path'] = str(fp.relative_to(dp))

    for t in obj:
        medias = (t.get("entities") or {}).get("media") or []
        [download(m) for m in medias]
        medias = (t.get("extended_entities") or {}).get("media") or []
        [download(m) for m in medias]

    write(json_path, json_stringify(obj, indent=2))
