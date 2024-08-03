from __future__ import annotations

import json
from pathlib import Path

import hypy_utils.downloader
from hypy_utils import write, json_stringify, ensure_dir
from hypy_utils.tqdm_utils import tmap


def download_media(json_path: Path, mt: bool = False):
    """
    Download media urls embedded in a twitter json to somewhere local

    :param json_path: Path to tweets.json
    :param mt: Multithread (might break progress bar display)
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
            url = v['url']
            fp = ensure_dir(dp / 'media' / 'video') / url.split("/")[-1].split("?")[0]
            if not fp.is_file():
                print(f"Downloading video {v}")
                hypy_utils.downloader.download_file(url, fp)
            media['local_video_path'] = str(fp.relative_to(dp))

    # Gather media objects
    medias = []
    for t in obj:
        medias += (t.get("entities") or {}).get("media") or []
        medias += (t.get("extended_entities") or {}).get("media") or []

    # Download
    if mt:
        tmap(download, medias, desc="Downloading medias")
    else:
        [download(m) for m in medias]

    write(json_path, json_stringify(obj, indent=2))
