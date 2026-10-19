#!/usr/bin/env python3
"""Compare deployed catalogs with local files and check current icons/IPA headers."""
import json
import time
import urllib.request
from pathlib import Path

from validate_source import remote_error, validate_data

ROOT = Path(__file__).resolve().parents[1]


def verify() -> None:
    urls = {}
    for path in sorted((ROOT / 'public').glob('*.json')):
        expected = json.loads(path.read_text(encoding='utf-8'))
        url = expected['sourceURL']
        if path.name == 'repo.json':
            url = url.rsplit('/', 1)[0] + '/repo.json'
        last_error = None
        for attempt in range(6):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'ios-source-publication-check'})
                with urllib.request.urlopen(req, timeout=60) as response:
                    if response.status != 200:
                        raise RuntimeError(f'HTTP {response.status}')
                    if response.headers.get_content_type() != 'application/json':
                        raise RuntimeError('Expected application/json')
                    actual = json.load(response)
                if actual != expected:
                    raise RuntimeError('Deployed catalog differs from the checked-out catalog')
                errors = validate_data(actual, allow_duplicate_bundles=path.name in ('apps.json', 'repo.json'))
                if errors:
                    raise RuntimeError('; '.join(errors))
                last_error = None
                break
            except Exception as error:
                last_error = error
                if attempt < 5:
                    time.sleep(10)
        if last_error:
            raise RuntimeError(f'{url}: {last_error}')
        print(f'OK: {url}', flush=True)
        for app in expected['apps']:
            urls[app['iconURL']] = True
            urls[app['versions'][0]['downloadURL']] = False
    for url, is_image in urls.items():
        if error := remote_error(url, image=is_image):
            raise RuntimeError(f'{url}: {error}')
        print(f'OK: {url}', flush=True)


if __name__ == '__main__':
    verify()
