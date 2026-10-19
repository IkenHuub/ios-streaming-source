import copy
import io
import json
import plistlib
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import update_source as updater
import validate_source as validator


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.public = self.root / 'public'
        self.config = copy.deepcopy(updater.load_json(updater.CONFIG_PATH, {}))
        self.config['apps'] = [next(a for a in self.config['apps'] if a['id'] == 'nuvio-enhanced')]
        self.config['compatibleSources'] = []
        self.config_path = self.root / 'config.json'
        self.config_path.write_text(json.dumps(self.config))
        self.ipa = self.root / 'fixture.ipa'
        with zipfile.ZipFile(self.ipa, 'w') as archive:
            archive.writestr('Payload/Test.app/Info.plist', plistlib.dumps({
                'CFBundleIdentifier': 'com.nuvio.media', 'CFBundleShortVersionString': '0.6.2',
                'CFBundleVersion': '145', 'MinimumOSVersion': '16.1',
                'NSCameraUsageDescription': 'Use camera',
            }))
        self.release = {
            'id': 123, 'tag_name': '0.6.2-beta', 'published_at': '2026-10-19T04:08:19Z',
            'updated_at': '2026-10-19T04:08:19Z', 'body': 'Changes', 'assets': [{
                'id': 456, 'name': 'nuvio-0.6.2-enhanced-release.ipa', 'download_count': 1,
                'browser_download_url': 'https://github.com/luqmanfadlli/NuvioMobile-Enhanced/releases/download/0.6.2-beta/nuvio-0.6.2-enhanced-release.ipa',
            }],
        }
        self.paths = patch.multiple(updater, CONFIG_PATH=self.config_path,
            PUBLIC_DIR=self.public, SOURCE_PATH=self.public / 'apps.json',
            ALIAS_PATH=self.public / 'repo.json', STATE_PATH=self.root / 'state.json')
        self.paths.start()
        self.addCleanup(self.paths.stop)
        self.latest = patch.object(updater, 'latest_release', return_value=self.release)
        self.latest.start()
        self.addCleanup(self.latest.stop)

    def download(self, url):
        target = self.root / 'download.ipa'
        target.write_bytes(self.ipa.read_bytes())
        return target

    def run_update(self, refresh=False):
        with patch.object(updater, 'download_ipa', side_effect=self.download) as download:
            changed = updater.update(refresh=refresh)
        return changed, download.call_count

    def test_enhanced_accepts_old_and_new_filenames(self):
        app = self.config['apps'][0]
        for name in ('nuvio-0.5.9-enhanced.ipa', 'nuvio-0.6.2-enhanced-release.ipa'):
            self.release['assets'][0]['name'] = name
            self.assertTrue(updater.select_ipa_url(self.release, False, app['ipaAssetPattern']))
        self.release['assets'][0]['name'] = 'nuvio-0.6.2-full-release.ipa'
        with self.assertRaisesRegex(RuntimeError, 'no permitted IPA'):
            updater.select_ipa_url(self.release, False, app['ipaAssetPattern'])

    def test_cache_is_deterministic_and_ignores_download_count(self):
        self.assertEqual(self.run_update(), (True, 1))
        original = (self.public / 'apps.json').read_bytes()
        self.release['assets'][0]['download_count'] += 1
        self.assertEqual(self.run_update(), (False, 0))
        self.assertEqual(original, (self.public / 'apps.json').read_bytes())
        self.assertEqual(self.run_update(refresh=True), (False, 1))

    def test_republished_same_build_refreshes_link_without_duplicate(self):
        self.run_update()
        self.release['assets'][0]['browser_download_url'] = self.release['assets'][0]['browser_download_url'].replace('.ipa', '-replacement.ipa')
        self.assertEqual(self.run_update(), (True, 1))
        app = json.loads((self.public / 'apps.json').read_text())['apps'][0]
        self.assertEqual(len(app['versions']), 1)
        self.assertTrue(app['versions'][0]['downloadURL'].endswith('-replacement.ipa'))

    def test_missing_ipa_fails_instead_of_silent_stale_success(self):
        self.run_update()
        before = (self.public / 'apps.json').read_bytes()
        self.release['assets'] = []
        with self.assertRaisesRegex(RuntimeError, 'no permitted IPA'):
            self.run_update()
        self.assertEqual(before, (self.public / 'apps.json').read_bytes())

    def test_rejects_unapproved_download_repository(self):
        self.release['assets'][0]['browser_download_url'] = 'https://github.com/attacker/fork/releases/download/x/app.ipa'
        with self.assertRaisesRegex(RuntimeError, 'configured repository'):
            self.run_update()
        self.assertFalse(self.public.exists())

    def test_no_output_written_when_validation_fails(self):
        self.config['apps'][0]['iconURL'] = 'http://example.org/icon.png'
        self.config_path.write_text(json.dumps(self.config))
        with self.assertRaisesRegex(RuntimeError, 'Invalid generated source'):
            self.run_update()
        self.assertFalse(self.public.exists())
        self.assertFalse((self.root / 'state.json').exists())

    def test_ipa_metadata_comes_from_plist(self):
        data = updater.ipa_metadata(self.ipa)
        self.assertEqual(data['bundleIdentifier'], 'com.nuvio.media')
        self.assertEqual(data['version'], '0.6.2')
        self.assertEqual(data['size'], self.ipa.stat().st_size)
        self.assertEqual(data['privacy']['NSCameraUsageDescription'], 'Use camera')
        with zipfile.ZipFile(self.ipa, 'w') as archive:
            archive.writestr('Payload/Test.app/Info.plist', plistlib.dumps({}))
        with self.assertRaisesRegex(RuntimeError, 'missing required metadata'):
            updater.ipa_metadata(self.ipa)

    def test_catalog_urls_and_duplicate_alias(self):
        self.run_update()
        source = json.loads((self.public / 'nuvio-enhanced.json').read_text())
        self.assertTrue(source['sourceURL'].endswith('/nuvio-enhanced.json'))
        self.assertEqual((self.public / 'apps.json').read_bytes(), (self.public / 'repo.json').read_bytes())


class ReleaseAndValidationTests(unittest.TestCase):
    def test_release_selection_paginates_past_prereleases(self):
        prereleases = [{'prerelease': True}] * 100
        release = {'id': 1, 'tag_name': '1.0', 'published_at': '2026-01-01'}
        with patch.object(updater, 'fetch_json', side_effect=[prereleases, [release]]):
            self.assertEqual(updater.latest_release('owner/repo'), release)

    def test_bad_json_types_return_errors(self):
        for source in (None, [], {'apps': [None]}, {'apps': [{'versions': [None]}]}):
            self.assertTrue(validator.validate_data(source))
        self.assertFalse(validator.https_url(None))

    def test_published_sources_validate(self):
        root = Path(__file__).resolve().parents[1]
        for path in (root / 'public').glob('*.json'):
            with self.subTest(path=path):
                self.assertEqual(validator.validate(path, allow_duplicate_bundles=path.name in ('apps.json', 'repo.json')), [])

    def test_boolean_size_and_reversed_dates_are_rejected(self):
        root = Path(__file__).resolve().parents[1]
        source = json.loads((root / 'public/apex.json').read_text())
        source['apps'][0]['versions'][0]['size'] = True
        source['apps'][0]['versions'][0]['date'] = '2000-01-01'
        errors = validator.validate_data(source)
        self.assertTrue(any('positive byte count' in e for e in errors))
        self.assertTrue(any('newest first' in e for e in errors))


if __name__ == '__main__':
    unittest.main()
