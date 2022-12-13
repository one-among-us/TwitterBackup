# TwitterBackup

A tool to back up other users' Twitter accounts using the Twitter API. (Currently limited to the last 3200 tweets).

https://user-images.githubusercontent.com/22280294/207434663-a2fa6170-d740-4f35-82f6-df41bdce8837.mp4

## Usage

1. Install python `>= 3.7` (Tested on python 3.11)
2. `pip install twb`
3. [Register for a Twitter API token](https://developer.twitter.com/en/portal/dashboard)
4. Put your tokens in `$HOME/.config/twb/config.toml` or `./config.toml`.   
  You can reference the example config below
5. Run command `twb <username>`, and it will download to `./backups`

#### Example Config

```toml
# The consumer key from the Twitter application portal (https://developer.twitter.com/en/portal/dashboard)
consumer_key = '#########################'
# The consumer secret from the Twitter application portal
consumer_secret = '##################################################'
# The access token of an app from the Twitter application portal
access_token = '##################################################'
# The access secret of an app from the Twitter application portal
access_secret = '#############################################'
```
