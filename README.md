# TwitterBackup
 Backup other users' twitter accounts with Twitter API

## Usage

1. Install python `>= 3.7` (Tested on python 3.11)
2. `pip install twb`
3. [Register for a Twitter API token](https://developer.twitter.com/en/portal/dashboard)
4. Put your tokens in `$HOME/.config/twb/config.toml` or `./config.toml`. You can reference the example config below
5. Run command `twb <username>`

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
