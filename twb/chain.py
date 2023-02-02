import json
import math
import random
import time

import tweepy
from hypy_utils import read, write, json_stringify
from .collect import calculate_rate_delay
from tweepy import API, User, TooManyRequests

USER_DIR = "../TwitterData/users"
KW = "⚧|🌈|mtf|ftm|mtx|ftx|nonbi|trans|药娘|🍥|含糖|无糖|家长党|hrt|they/them|she/they|he/they".lower().split("|")


def filter_user(user: User) -> bool:
    context: str = user.name + user.description + user.id + user.location + user.screen_name
    context = context.lower()

    return any(w in context for w in KW)


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
    meta = json.loads(read(f'{USER_DIR}/meta/meta.json'))

    # Resume
    download_users_execute(api, meta['n'],
                           set(meta['downloaded']), set(meta['done_set']),
                           set(meta['current_set']), set(meta['next_set']))


def download_users_execute(api: API, n: float,
                           downloaded: set[str], done_set: set[str],
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
    rate_delay = calculate_rate_delay(1) + 1

    print("Executing friends-chain download:")
    print(f"- n: {n}")
    print(f"- Requests per minute: {1}")
    print(f"- Directory: {USER_DIR}")
    print(f"- Downloaded: {len(downloaded)}")
    print(f"- Current search set: {len(current_set)}")
    print(f"- Next search set: {len(next_set)}")
    print()

    # Loop until there are enough users
    while len(downloaded) < n:
        # Take a screen name from the current list
        screen_name = current_set.pop()

        try:
            # # Get a list of friend ids
            friends: list[User] = api.get_friends(screen_name=screen_name, count=200)
            # friends: list[str] = []
            # for lst in tweepy.Cursor(api.get_friend_ids, screen_name=screen_name, count=5000).pages(limit=5):
            #     friends.extend(lst)
            #     time.sleep(calculate_rate_delay(1))
            #
            # # Crawl each friend that doesn't exist
            # dne = [f for f in friends if f not in done_ids]
            # users = []
            # [user.screen_name for user in api.lookup_users(user_ids=friends)]

        except TooManyRequests:
            # Rate limited, sleep and try again
            print('Caught TooManyRequests exception: Rate limited, sleep and try again.')
            time.sleep(rate_delay)
            current_set.add(screen_name)
            continue

        # Save users
        for user in friends:
            # This user was not saved, save the user.
            if user not in downloaded:
                # Save user json
                write(f'{USER_DIR}/users/{user.screen_name}.json', json_stringify(user._json))

                # Add to set
                downloaded.add(user.screen_name)
                # debug(f'- Downloaded {user.screen_name}')

        # Filter users
        friends = [u for u in friends if filter_user(u)]

        # Get users and their popularity that we haven't downloaded
        screen_names = [(u.screen_name, u.followers_count) for u in friends
                        if u.screen_name not in done_set and not u.protected]

        # Sort by followers count, from least popular to most popular
        screen_names.sort(key=lambda x: x[1])

        # Add 3 random users to the next set
        # python_ta thinks that u is not indexable but it is, because it is a tuple of length 2
        if len(screen_names) > 3:
            samples = {u[0] for u in random.sample(screen_names, 3)}
        else:
            samples = {u[0] for u in screen_names}

        # Add the selected users to the next set
        for s in samples:
            next_set.add(s)

        # Change name lists
        if len(current_set) == 0:
            current_set = next_set
            next_set = set()

        # This one is done
        done_set.add(screen_name)

        # Update meta info so that downloading can be continued
        meta = {'downloaded': downloaded, 'done_set': done_set,
                'current_set': current_set, 'next_set': next_set, 'n': n}
        write(f'{USER_DIR}/meta/meta.json', json_stringify(meta))

        print(f'Finished saving friends of {screen_name}')
        print(f'============= Total {len(downloaded)} saved =============')

        # Rate limit
        time.sleep(rate_delay)


def test_main(api: API):
    f = api.get_friends(screen_name="sauricat", count=200)

    print("hi")
