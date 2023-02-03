import json
import math
import os
import random
import string
import time
from pathlib import Path
from traceback import print_exc
from types import SimpleNamespace

import tweepy
from hypy_utils import read, write, json_stringify, jsn
from hypy_utils.tqdm_utils import pmap
from twb.utils import debug

from .collect import calculate_rate_delay, download_all_tweets, download_media
from tweepy import API, User, TooManyRequests, Unauthorized

DATA_DIR = Path("../twitter-data")
USER_DIR = DATA_DIR / "user"
META_DIR = USER_DIR / 'meta/meta-new.json'
KW = set("⚧|🌈|mtf|ftm|mtx|ftx|nonbi|trans |transgender|transmasc|transfem|"
         "药娘|飞天猫|🍥|含糖|无糖|家长党|hrt|they/them|she/they|he/they".lower().split("|"))


def filter_kw(s: str) -> bool:
    s = s.lower() + " "
    # Replace punctuations for whole-word matching
    for p in string.punctuation:
        s = s.replace(p, " ")
    return any(w in s for w in KW)


def filter_user(u: dict) -> bool:
    return filter_kw(u['name'] + u['description'] + u['location'] + u['screen_name'])


def download_users_start(api: API, start_point: str, n: float = math.inf) -> None:
    """
    This function downloads n Twitter users by using a friends-chain.
    Since there isn't an API or a database with all Twitter users, we can't obtain a strict list
    of all Twitter users, nor can we obtain a list of strictly random or most popular Twitter
    users. Therefore, we use the method of follows chaining: we start from a specific individual,
    obtain their followers, and pick 6 random individuals from the friends list. Then, we repeat
    the process for the selected friends: we pick 6 random friends of the 6 random friends
    that we picked.
    In reality, this method will be biased toward individuals that are worthy of following since
    "friends" are the list of users that someone followed.
    Data Directory
    --------
    It will download all user data to ./data/twitter/user/users/<screen_name>.json
    It will save meta info to ./data/twitter/user/meta/
    Twitter API Reference
    --------
    It will be using the API endpoint api.twitter.com/friends/list (Documentation:
    https://developer.twitter.com/en/docs/twitter-api/v1/accounts-and-users/follow-search-get-users/api-reference/get-friends-list)
    This will limit the rate of requests to 15 requests in a 15-minute window, which is one request
    per minute. But it is actually the fastest method of downloading a wide range of users on
    Twitter because it can download a maximum of 200 users at a time while the API for downloading
    a single user is limited to only 900 queries per 15, which is only 60 users per minute.
    There is another API endpoint that might do the job, which is api.twitter.com/friends/ids (Doc:
    https://developer.twitter.com/en/docs/twitter-api/v1/accounts-and-users/follow-search-get-users/api-reference/get-friends-ids)
    However, even though this endpoint has a much higher request rate limit, it only returns user
    ids and not full user info.
    Parameters
    --------
    :param api: Tweepy's API object
    :param start_point: Starting user's screen name.
    :param n: How many users do you want to download? (Default: math.inf)
    :return: None
    """

    # Set of all the downloaded users' screen names
    downloaded = set()

    # The set of starting users that are queried.
    done_set = set()

    # The set of starting users currently looping through
    current_set = {start_point}

    # The next set of starting users
    next_set = set()

    # Start download
    download_users_execute(api, n, downloaded, done_set, current_set, next_set)


def download_users_resume_progress(api: API) -> None:
    """
    Resume from started progress
    :param api: Tweepy's API object
    :return: None
    """
    # Open file and read
    meta = json.loads(read(META_DIR))

    # Resume
    downloaded = {str(f) for f in os.listdir(USER_DIR / 'users-new') if str(f).endswith(".json")}
    download_users_execute(api, meta['n'],
                           downloaded, set(meta['done_set']),
                           set(meta['current_set']), set(meta['next_set']))


def _json_namespace_helper(p: Path) -> SimpleNamespace:
    return jsn(p.read_text())


def download_users_execute(api: API, n: float,
                           downloaded: set[int], done_set: set[str],
                           current_set: set[str], next_set: set[str]) -> None:
    """
    Execute download from the given parameters. The download method is defined in the document for
    the download_users function.
    Resume functionality is necessary because twitter limits the rate of get friends list to 15
    requests in a 15-minute window, which is 1 request per minute, so it will take a long time to
    gather enough data, so we don't want to have to start over from the beginning once something
    goes wrong.
    :param api: Tweepy's API object
    :param n: How many users do you want to download?
    :param downloaded: Set of all the downloaded users' screen names
    :param done_set: The set of starting users that are queried
    :param current_set: The set of starting users currently looping through
    :param next_set: The next set of starting users
    :return: None
    """
    # Rate limit for this API endpoint is 1 request per minute, and rate delay defines how many
    # seconds to sleep for each request.
    rate_delay_15_15 = calculate_rate_delay(1) + 1
    rate_delay_900_15 = calculate_rate_delay(900 / 15)

    print("Executing friends-chain download:")
    print(f"- n: {n}")
    print(f"- Requests per minute: {1}")
    print(f"- Directory: {USER_DIR.absolute()}")
    print(f"- Downloaded: {len(downloaded)}")
    print(f"- Current search set: {len(current_set)}")
    print(f"- Next search set: {len(next_set)}")
    print()

    # Loop until there are enough users
    while len(downloaded) < n:
        # Take a screen name from the current list
        screen_name = current_set.pop()
        debug(f"Starting friend-chain from {screen_name}")

        # Start time for get_friend_ids rate limit
        rate_start_time = time.time()

        try:
            # Get a list of friend ids
            ids: list[int] = []
            for lst in tweepy.Cursor(api.get_friend_ids, screen_name=screen_name, count=5000).pages(limit=5):
                # Rate delay starting on the second iteration
                if ids:
                    time.sleep(rate_delay_15_15)
                    rate_start_time = time.time()

                ids.extend(lst)
                debug(f"> Obtained {len(ids)} friend ids in total.")

            # Crawl each friend that doesn't exist
            dne = [f for f in ids if f not in downloaded]
            while dne:
                # max 100 users at a time
                seg = dne[:100]
                dne = dne[100:]

                # crawl users
                users = api.lookup_users(user_id=seg)
                time.sleep(rate_delay_900_15)
                debug(f"> Saved {len(users)} user jsons, {len(dne)} left")

                for u in users:
                    # Save user json
                    write(USER_DIR / f'users-new/{u.id}.json', json_stringify(u._json))
                    write(USER_DIR / f'users/{u.screen_name}.json', json_stringify(u._json))
                    downloaded.add(u.id)

            # Read jsons
            jsons = [USER_DIR / f'users-new/{u}.json' for u in ids]
            jsons_safe = [j for j in jsons if j.is_file()]
            if len(jsons_safe) != len(jsons):
                print("ERROR: At least one json id exist in downloads but has no associated json file:")
                print(set(jsons) - set(jsons_safe))
            friends: list[dict] = pmap(_helper_load_json, jsons_safe)

        except TooManyRequests:
            # Rate limited, sleep and try again
            debug('Caught TooManyRequests exception: Rate limited, sleep and try again.')
            time.sleep(120)
            current_set.add(screen_name)
            continue

        except Unauthorized as e:
            debug(f'{screen_name}: Skipping - unauthorized: {e}')
            print_exc()
            continue

        # Filter users
        friends = [u for u in friends if filter_user(u)]

        # Get users and their popularity that we haven't downloaded
        screen_names = [u['screen_name'] for u in friends if u['screen_name'] not in done_set and not u['protected']]

        # Add all users to the next set
        next_set.update(screen_names)

        # Change name lists
        if len(current_set) == 0:
            current_set = next_set
            next_set = set()

        # This one is done
        done_set.add(screen_name)

        # Update meta info so that downloading can be continued
        meta = {'done_set': list(done_set), 'current_set': list(current_set), 'next_set': list(next_set), 'n': n}
        write(META_DIR, json_stringify(meta))

        debug(f'Finished saving friends of {screen_name} (added {len(screen_names)})')
        debug(f'============= Total {len(downloaded)} saved =============')

        # If the elapsed time is lower than the rate limit, sleep
        delta = rate_delay_15_15 - (time.time() - rate_start_time)
        if delta > 0:
            debug(f"Sleeping {delta:.2f}s")
            time.sleep(delta)


def chain_exp(api: API):
    # download_users_start(api, "sauricat")
    download_users_resume_progress(api)


def _helper_load_json(p: Path):
    return json.loads(p.read_text())


def chain_dl(api: API):
    print("Downloading...")

    # Load all user jsons
    users_dir = Path(USER_DIR) / "users"
    users = [users_dir / f for f in os.listdir(users_dir) if f.endswith(".json")]
    users = pmap(_helper_load_json, users, desc="Loading jsons", chunksize=5000)
    print(f"Loaded {len(users)} users.")

    # Filter trans users
    users = [u for u in users if filter_user(u)]
    print(f"Total of {len(users)} users after filtering.")

    # Download backup for each user
    for u in users:
        udir = DATA_DIR / "backups" / u['screen_name']
        if udir.is_dir():
            continue

        try:
            download_all_tweets(api, u['screen_name'], udir / "tweets.json")
        except Exception as e:
            print(f"Skipped {u} because: {e}")
            print_exc()
            time.sleep(30)
            continue


def chain_media():
    print("Downloading media...")

    # Load all user jsons
    backup_dir = DATA_DIR / "backups"

    # Download backup for each user
    for u in os.listdir(backup_dir):
        udir = backup_dir / str(u) / "tweets.json"

        try:
            download_media(udir, mt=True)
        except Exception as e:
            print(f"Skipped {u} because: {e}")
            print_exc()
            time.sleep(30)
            continue
