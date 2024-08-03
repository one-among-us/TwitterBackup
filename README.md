# TwitterBackup

A tool to back up other users' Twitter accounts using the Twitter API. (Currently limited to the last 3200 tweets).

https://user-images.githubusercontent.com/22280294/207434663-a2fa6170-d740-4f35-82f6-df41bdce8837.mp4

## Usage

1. Install python `>= 3.9` (Tested on python 3.12)
2. `pip install twb>2.0`
3. Dump your cookies using the EditThisCookie extension, save it in `./cookies.json`
4. Run command `twb <username>`, and it will download to `./backups`
