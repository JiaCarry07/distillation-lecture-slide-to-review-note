"""Regression checks for offline asset handling and chapter validation."""

import base64
import contextlib
import hashlib
import io
import json
import pathlib
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

from scripts import check_chapter, ensure_katex

TEST_DIR = pathlib.Path(__file__).resolve().parent


def make_archive(extra_name=None):
    buffer = io.BytesIO()
    names = [
        "package/dist/katex.min.css",
        "package/dist/katex.min.js",
        "package/dist/contrib/auto-render.min.js",
    ]
    if extra_name:
        names.append(extra_name)
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name in names:
            data = b"test asset"
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def run_download(destination, archive, digest=None):
    digest = digest or hashlib.sha512(archive).digest()
    integrity = "sha512-" + base64.b64encode(digest).decode("ascii")
    metadata = json.dumps({"dist": {"integrity": integrity}}).encode("utf-8")

    def fake_urlopen(url, timeout):
        return io.BytesIO(metadata if "/katex/0.16.11" in url else archive)

    with mock.patch.object(ensure_katex.urllib.request, "urlopen", fake_urlopen), \
         mock.patch.object(sys, "argv", ["ensure_katex.py", str(destination)]), \
         contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()):
        return ensure_katex.main()


class KaTeXDownloadTests(unittest.TestCase):
    def test_verified_archive_extracts_assets(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIR) as tmp:
            self.assertEqual(run_download(tmp, make_archive()), 0)
            self.assertTrue((pathlib.Path(tmp) / "package/dist/katex.min.js").is_file())

    def test_bad_digest_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIR) as tmp:
            self.assertEqual(run_download(tmp, make_archive(), b"x" * 64), 1)
            self.assertFalse((pathlib.Path(tmp) / "package/dist/katex.min.js").exists())

    def test_archive_cannot_escape_dist(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIR) as tmp:
            archive = make_archive("package/dist/../../outside.txt")
            with self.assertRaises(ValueError):
                run_download(tmp, archive)
            self.assertFalse((pathlib.Path(tmp) / "outside.txt").exists())


class ChapterChecks(unittest.TestCase):
    def test_flags_inline_fraction_and_raw_angle_bracket(self):
        source = ('<h1 class="chap"><span class="cn">CHAPTER 1</span>示例</h1>'
                  '<p>$\\frac{1}{2}$ 与 $a<b$</p>')
        errors, _, _ = check_chapter.inspect(source, 1)
        self.assertTrue(any("行内公式" in message for message in errors))
        self.assertTrue(any("未转义" in message for message in errors))


if __name__ == "__main__":
    unittest.main()
