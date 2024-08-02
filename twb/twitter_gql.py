import json
import time
from collections import Counter
from pathlib import Path

import requests
from hypy_utils import ensure_parent, write_json
from hypy_utils.logging_utils import setup_logger

log = setup_logger()


class TwitterRequester:
    HTTP = requests.session()

    def __init__(self, cookies: str) -> None:
        # Parse json cookie
        bacon: list[dict] = json.loads(cookies)
        bacon: dict = {d['name']: d['value'] for d in bacon}

        [self.HTTP.cookies.set(k, v) for k, v in bacon.items()]
        self.HTTP.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
            'Authorization': f'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'x-csrf-token': bacon['ct0']
        })

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

        return self._request('https://x.com/i/api/graphql/xmU6X_CKVnQ5lSrCbAmJsg/UserByScreenName', v, f, t)['data']['user']['result']

    def user_tweets(self, user_id: int, cursor: str | None = None) -> (list, str, str):
        """
        :return: Tweets, last cursor, next cursor
        """
        v = {"userId": str(user_id), "count": 20, "includePromotedContent": False, "withCommunity": True,
             "withVoice": True, "withV2Timeline": True}
        if cursor:
            v['cursor'] = cursor
        f = {"rweb_tipjar_consumption_enabled": True, "responsive_web_graphql_exclude_directive_enabled": True,
             "verified_phone_label_enabled": False, "creator_subscriptions_tweet_preview_api_enabled": True,
             "responsive_web_graphql_timeline_navigation_enabled": True,
             "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
             "communities_web_enable_tweet_community_results_fetch": True,
             "c9s_tweet_anatomy_moderator_badge_enabled": True, "articles_preview_enabled": True,
             "responsive_web_edit_tweet_api_enabled": True,
             "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
             "view_counts_everywhere_api_enabled": True, "longform_notetweets_consumption_enabled": True,
             "responsive_web_twitter_article_tweet_consumption_enabled": True,
             "tweet_awards_web_tipping_enabled": False, "creator_subscriptions_quote_tweet_preview_enabled": False,
             "freedom_of_speech_not_reach_fetch_enabled": True, "standardized_nudges_misinfo": True,
             "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
             "rweb_video_timestamps_enabled": True, "longform_notetweets_rich_text_read_enabled": True,
             "longform_notetweets_inline_media_enabled": True, "responsive_web_enhance_cards_enabled": False}
        t = {"withArticlePlainText": False}

        inst: dict = self._request('https://x.com/i/api/graphql/bt4TKuFz4T7Ckk-VvQVSow/UserTweetsAndReplies', v, f, t)
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

    def crawl_all(self, screen_name: str, rate_delay: float = 10) -> None:
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
            time.sleep(rate_delay)

    def _request(self, url: str, variables: dict, features: dict, field_toggles: dict) -> dict:
        resp = self.HTTP.get(url, headers={
            'x-csrf-token': self.HTTP.cookies.get('ct0')
        }, params={
            'variables': json.dumps(variables),
            'features': json.dumps(features),
            'fieldToggles': json.dumps(field_toggles),
        })
        resp.raise_for_status()
        return resp.json()


if __name__ == '__main__':
    # Load cookies from a JSON export of EditThisCookie
    requester = TwitterRequester(Path('cookies.json').read_text())

    # Crawl all tweets
    requester.crawl_all('hykilpikonna')

    # # Make requests
    # response = requester.user_by_screen_name('hykilpikonna')
    # print(json.dumps(response, indent=2, sort_keys=True, ensure_ascii=False))
    #
    # id = response['rest_id']
    #
    # response = requester.user_tweets(id)
    # print(response)
