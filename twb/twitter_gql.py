import json
import os
import time
from collections import Counter
from pathlib import Path

import orjson
import pandas as pd
import requests
from hypy_utils import ensure_parent, write_json, ensure_dir
from hypy_utils.logging_utils import setup_logger
from hypy_utils.tqdm_utils import tmap

from twb.gql_consts import TWEETS_F

log = setup_logger()
cache_dir = ensure_dir(Path(__file__).parent / '.cache')
RATE_DELAY = 1


class TwitterGQL:
    HTTP = requests.session()
    cookie_sets: list[dict] = []
    cookie_idx = 0

    def __init__(self, cookies: Path, base_dir: Path = Path('backups')):
        self.base_dir = Path(base_dir)

        # Check if alts.csv exist
        if (cookies / 'alts.csv').exists():
            # screen_name, password, 2fa, email, email_password, auth_token, ct0
            v = pd.read_csv(cookies / 'alts.csv').to_dict(orient='records')
            self.cookie_sets += [{
                'auth_token': d['auth_token'],
                'ct0': d['ct0']
            } for d in v]

        # Load all cookie files
        for cf in cookies.glob('*.json'):
            bacon = json.loads(cf.read_text())
            self.cookie_sets.append({d['name']: d['value'] for d in bacon})
        assert self.cookie_sets, 'No cookies loaded'
        self.set_cookie(0)

    def set_cookie(self, idx: int):
        bacon = self.cookie_sets[idx]

        [self.HTTP.cookies.set(k, v) for k, v in bacon.items()]
        self.HTTP.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
            'Authorization': f'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'x-csrf-token': bacon['ct0']
        })

    def rotate_cookie(self):
        self.cookie_idx = (self.cookie_idx + 1) % len(self.cookie_sets)
        log.error(f"Rotating cookie to {self.cookie_idx}...")
        self.set_cookie(self.cookie_idx)

    def user_by_screen_name(self, screen_name: str) -> dict:
        v = {"screen_name": screen_name, "withSafetyModeUserFields": True}
        f = {"hidden_profile_subscriptions_enabled": True, "rweb_tipjar_consumption_enabled": True,
             "responsive_web_graphql_exclude_directive_enabled": True, "verified_phone_label_enabled": False,
             "subscriptions_verification_info_is_identity_verified_enabled": True,
             "subscriptions_verification_info_verified_since_enabled": True, "highlights_tweets_tab_ui_enabled": True,
             "responsive_web_twitter_article_notes_tab_enabled": True, "subscriptions_feature_can_gift_premium": False,
             "creator_subscriptions_tweet_preview_api_enabled": True,
             "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
             "responsive_web_graphql_timeline_navigation_enabled": True}
        t = {"withAuxiliaryUserLabels": False}
        r = self._request('https://x.com/i/api/graphql/xmU6X_CKVnQ5lSrCbAmJsg/UserByScreenName', v, f, t)
        return r['data']['user']['result']

    def user_tweets(self, user_id: int, cursor: str | None = None) -> (list, str, str):
        """
        :return: Tweets, last cursor, next cursor
        """
        v = {"userId": str(user_id), "count": 20, "includePromotedContent": False, "withCommunity": True,
             "withVoice": True, "withV2Timeline": True}
        if cursor:
            v['cursor'] = cursor
        f = TWEETS_F
        t = {"withArticlePlainText": False}

        inst: dict = self._request('https://x.com/i/api/graphql/bt4TKuFz4T7Ckk-VvQVSow/UserTweetsAndReplies', v, f, t)
        time.sleep(RATE_DELAY)
        inst: list = inst['data']['user']['result']['timeline_v2']['timeline']['instructions']

        # Find type=TimelineAddEntries
        tl: list = next(i for i in inst if i['type'] == 'TimelineAddEntries')['entries']
        if not tl:
            raise RuntimeError('No TimelineAddEntries')

        # Map to content
        tl = [t['content'] for t in tl]

        # Count types
        type_count = Counter(t['__typename'].replace('Timeline', '') for t in tl)
        log.info(f'+ {type_count}')

        # Find items
        tweets = [t for t in tl if t['__typename'] != 'TimelineTimelineCursor']

        # Find cursors
        cursors = {t['cursorType']: t['value'] for t in tl if t['__typename'] == 'TimelineTimelineCursor'}

        return tweets, cursors['Top'], cursors['Bottom']

    def tweet_detail(self, tweet_id: str | int):
        fp = cache_dir / f'tweet_detail/{tweet_id}.json'
        if fp.exists():
            r = orjson.loads(fp.read_bytes())
        else:
            v = {"focalTweetId": str(tweet_id), "referrer": "tweet", "with_rux_injections": False,
                 "rankingMode": "Relevance", "includePromotedContent": True, "withCommunity": True,
                 "withQuickPromoteEligibilityTweetFields": True, "withBirdwatchNotes": True, "withVoice": True}
            f = TWEETS_F
            t = {"withArticleRichContentState": True, "withArticlePlainText": False, "withGrokAnalyze": False,
                 "withDisallowedReplyControls": False}
            r: dict = self._request('https://x.com/i/api/graphql/nBS-WpgA6ZG0CyNHD517JQ/TweetDetail', v, f, t)
            time.sleep(RATE_DELAY)
            write_json(fp, r)
        if r.get('errors'):
            log.warning(f'Error: {r["errors"]}')
            if 'AuthorizationError' in str(r['errors']):
                os.remove(fp)
                os._exit(0)
            return []
        r: list = r['data']['threaded_conversation_with_injections_v2']['instructions']

        # Parse
        r: list = [inst for inst in r if inst['type'] == 'TimelineAddEntries']
        assert len(r) <= 1
        if not r:
            log.debug(f'No TimelineAddEntries for {tweet_id}')
            return []
        r: list = r[0]['entries']
        return r

    def _dfs_find_tweets(self, d):
        if isinstance(d, dict):
            return [d] if d.get('__typename') == 'Tweet' \
                else [d['tweet']] if d.get('__typename') == 'TweetWithVisibilityResults' \
                else sum([self._dfs_find_tweets(value) for value in d.values()], [])
        elif isinstance(d, list):
            return sum([self._dfs_find_tweets(item) for item in d], [])
        return []

    def crawl_parent(self, tweet_id: str | int):
        """
        From this tweet, crawl all its parent tweets until the root tweet
        """
        tweet_id = str(tweet_id)
        file = self.base_dir / f'twb/by-id/{tweet_id[:2]}/{tweet_id}.json'
        if file.exists():
            d = orjson.loads(file.read_bytes())
            rep = d['legacy'].get('in_reply_to_status_id_str')
            return self.crawl_parent(rep) if rep else None

        log.info(f'Crawling parent of {tweet_id}...')
        _d = self.tweet_detail(tweet_id)
        if not _d:
            log.warning(f'No data for {tweet_id}')
            return
        d = self._dfs_find_tweets(_d)

        # Save all tweets to file
        def save_tweet(t: dict):
            fp = ensure_parent(self.base_dir / f'twb/by-id/{t["rest_id"][:2]}/{t["rest_id"]}.json')
            write_json(fp, t) if not fp.exists() else None
            return t["rest_id"] == tweet_id

        if not any(map(save_tweet, d)):
            log.warning(f'Root tweet not found for {tweet_id}')
            return
        self.crawl_parent(tweet_id)

    def crawl_all(self, screen_name: str) -> None:
        """
        Crawl all tweets of a user
        """
        log.info(f'Crawling {screen_name}...')
        fp = ensure_parent(f'backups/{screen_name}/tweets.json')

        # Load progress
        all_tweets, last_top, last_bottom = [], None, None
        if fp.exists():
            all_tweets, last_top, last_bottom = json.loads(fp.read_text('utf-8'))

        # Screen name to user id
        id = self.user_by_screen_name(screen_name)['rest_id']

        while True:
            tweets, last_top, last_bottom = self.user_tweets(id, last_bottom)

            all_tweets.extend(tweets)
            write_json(fp, [all_tweets, last_top, last_bottom], indent=2)
            log.info(f'Got total {len(all_tweets)} tweets')
            if last_top == last_bottom or len(tweets) == 0:
                log.info(f'Done: {len(all_tweets)} tweets')
                break

    def _request(self, url: str, variables: dict, features: dict, field_toggles: dict, retries: int = None) -> dict:
        if retries is None:
            retries = len(self.cookie_sets)
        if retries == 0:
            raise RuntimeError('Retries exhausted')

        resp = self.HTTP.get(url, headers={'x-csrf-token': self.HTTP.cookies.get('ct0')}, params={
            'variables': json.dumps(variables),
            'features': json.dumps(features),
            'fieldToggles': json.dumps(field_toggles),
        })
        # Rate limit
        if resp.status_code == 429:
            log.error('Rate limited')
            self.rotate_cookie()
            return self._request(url, variables, features, field_toggles, retries - 1)

        resp.raise_for_status()
        return resp.json()
