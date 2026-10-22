#!/usr/bin/env python3
"""Header restoration authenticates API listings without forwarding credentials to downloads."""
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('prepare', Path(__file__).with_name('prepare-xnu-source.py'))
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class HeaderDownloadTests(unittest.TestCase):
    def test_api_credentials(self):
        for token in ('test-token', ''):
            with self.subTest(authenticated=bool(token)), patch.dict(prepare.os.environ, {'GH_TOKEN': token}, clear=True), \
                 patch.object(prepare.urllib.request, 'urlopen', return_value=io.BytesIO(b'[]')) as fetch:
                self.assertEqual(prepare.github_json(prepare.URL), b'[]')
                request = fetch.call_args.args[0]
                self.assertEqual(request.get_header('Authorization'), f'Bearer {token}' if token else None)
                self.assertEqual(request.get_header('Accept'), 'application/vnd.github+json')

    def test_raw_download_verifies_blob_without_token(self):
        data = b'// header\n'
        digest = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        entry = dict(type='file', name='test.h', download_url='https://raw.githubusercontent.com/apple/test.h', sha=digest)
        with tempfile.TemporaryDirectory() as directory, patch.dict(prepare.os.environ, {'GH_TOKEN': 'test-token'}), \
             patch.object(prepare.urllib.request, 'urlopen', return_value=io.BytesIO(data)) as fetch:
            destination = Path(directory)
            prepare.restore(entry, destination)
            self.assertEqual(fetch.call_args.args[0], entry['download_url'])
            self.assertEqual((destination / 'test.h').read_bytes(), data)
            with self.assertRaisesRegex(ValueError, 'Git blob hash mismatch'):
                prepare.restore(dict(entry, name='bad.h', sha='0' * 40), destination)
            self.assertFalse((destination / 'bad.h').exists())


if __name__ == '__main__':
    unittest.main()
