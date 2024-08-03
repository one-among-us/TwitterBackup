from __future__ import annotations

import json
from pathlib import Path

import hypy_utils.downloader
from hypy_utils import write, json_stringify, ensure_dir
from hypy_utils.tqdm_utils import tmap


def download_media(json_path: Path, mt: bool = False):
    """
    Download media URLs embedded in a Twitter JSON to somewhere local (v2)

    v2: Recursively search for "media_url_https" in the entire JSON tree instead of just the top level and just entities

    :param json_path: Path to tweets.json
    :param mt: Multithread (might break progress bar display)
    """
    dp = json_path.parent
    obj = json.loads(json_path.read_text())

    def download(url: str):
        fp = ensure_dir(dp / 'media') / url.split("/")[-1]
        if fp.is_file():
            return
        hypy_utils.downloader.download_file(url, fp)

    def extract_media_urls(o: list | dict, target_key) -> list:
        if isinstance(o, dict):
            for k, v in o.items():
                if k == target_key:
                    yield o[target_key]
                else:
                    yield from extract_media_urls(v, target_key)
        elif isinstance(o, list):
            for item in o:
                yield from extract_media_urls(item, target_key)

    # Gather media objects
    medias = list(extract_media_urls(obj, 'media_url_https'))

    # Gather video objects
    videos = list(extract_media_urls(obj, 'video_info'))
    videos = [max(v['variants'], key=lambda x: x.get('bitrate') or 0)['url'] for v in videos]
    medias += videos

    # Download
    if mt:
        tmap(download, medias, desc="Downloading medias")
    else:
        [download(m) for m in medias]


if __name__ == '__main__':
    download_media(Path('backups/zzj876/tweets.json'))