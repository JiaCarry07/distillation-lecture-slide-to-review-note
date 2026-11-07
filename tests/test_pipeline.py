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

from scripts import ensure_katex, bootstrap, chapter_map, render, finalize
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from scripts import enhance_navigation

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


class ProjectTests(unittest.TestCase):
    def test_page_number_positions_and_footer_do_not_overlap(self):
        for position, expected in (("right", ("right", "right")),
                                   ("outer", ("right", "left")),
                                   ("left", ("left", "left")),
                                   ("center", ("center", "center"))):
            with self.subTest(position=position), render.pymupdf.open() as doc:
                for _ in range(4):
                    doc.new_page(width=render.PAGE_W, height=render.PAGE_H)
                render.stamp_footer(doc, skip_first=2, left_text="Note", page_number_position=position)
                self.assertEqual(doc[0].get_text().strip(), "")
                for i, side in ((2, expected[0]), (3, expected[1])):
                    words = doc[i].get_text("words")
                    number = next(w for w in words if w[4] == str(i - 1))
                    footer = next(w for w in words if w[4] == "Note")
                    midpoint = (number[0] + number[2]) / 2
                    if side == "left":
                        self.assertLess(midpoint, render.PAGE_W * 0.25)
                        self.assertGreater(footer[0], render.PAGE_W * 0.5)
                    elif side == "right":
                        self.assertGreater(midpoint, render.PAGE_W * 0.75)
                        self.assertLess(footer[2], render.PAGE_W * 0.5)
                    else:
                        self.assertAlmostEqual(midpoint, render.PAGE_W / 2, delta=1)

    def test_outer_parity_starts_at_body_even_with_odd_front_matter(self):
        with render.pymupdf.open() as doc:
            for _ in range(3):
                doc.new_page(width=render.PAGE_W, height=render.PAGE_H)
            render.stamp_footer(doc, skip_first=1, page_number_position="outer")
            first = next(w for w in doc[1].get_text("words") if w[4] == "1")
            second = next(w for w in doc[2].get_text("words") if w[4] == "2")
            self.assertGreater(first[0], render.PAGE_W * 0.75)
            self.assertLess(second[2], render.PAGE_W * 0.25)

    def test_toc_and_total_use_body_numbers(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIR) as tmp:
            folder = pathlib.Path(tmp)
            cover = folder / 'cover.html'
            cover.write_text((TEST_DIR.parent / 'examples' / 'cover.html').read_text(encoding='utf-8'), encoding='utf-8')
            first, second = folder / 'ch01.html', folder / 'ch02.html'
            first.write_text('<p>first</p>', encoding='utf-8')
            second.write_text('<p>second</p>', encoding='utf-8')
            with mock.patch.object(finalize, 'COVER', cover):
                finalize.patch_cover([(1, 'First', first), (2, 'Second', second)], {1: 4, 2: 6}, 7, 'Title')
            result = cover.read_text(encoding='utf-8')
            self.assertIn('data-pg="total">4</span>', result)
            self.assertIn('data-pg="1">1</td>', result)
            self.assertIn('data-pg="2">3</td>', result)

    def test_chapter_number_does_not_absorb_next_line(self):
        match = finalize.CHAPTER_RE.search('C H A P T E R 2\n6 V')
        self.assertEqual(match.group(1).strip(), '2')

    def test_navigation_uses_each_chapter_anchor(self):
        class Page:
            def __init__(self, text): self.text = text
            def get_text(self): return self.text
        class Doc:
            pages = [Page('cover'), Page('contents'), Page('C H A P T E R 1\n第一章'),
                     Page('C H A P T E R 2\n6 V')]
            page_count = 4
            def __getitem__(self, index): return self.pages[index]
        headings = [[1, '封面', '封面', None], [1, '目录', '目录', None],
                    [1, 'CHAPTER1第一章', '第一章', 1], [1, 'CHAPTER2第二章', '第二章', 2]]
        toc, missed = enhance_navigation.locate(Doc(), headings)
        self.assertFalse(missed)
        self.assertEqual(toc[-1], [1, '第二章', 4])

    def test_bootstrap_preserves_existing_chapter(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIR) as tmp:
            with mock.patch.object(sys, "argv", ["bootstrap.py", tmp, "--example"]), contextlib.redirect_stdout(io.StringIO()):
                bootstrap.main()
                chapter = pathlib.Path(tmp) / ".courseware-note-studio/build/parts/ch01.html"
                chapter.write_text("user content", encoding="utf-8")
                bootstrap.main()
            self.assertEqual(chapter.read_text(encoding="utf-8"), "user content")
            self.assertTrue((chapter.parent / "ch02.html").exists())

    def test_chapter_mapping_validates_ranges(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIR) as tmp:
            path = pathlib.Path(tmp) / "chapter_map.json"
            path.write_text(json.dumps({"chapters":[{"number":1,"title":"Example","sources":[{"id":"f01","pages":[1,4]}]}]}), encoding="utf-8")
            mapping, titles = chapter_map.load_chapter_map(path)
            self.assertEqual(mapping[1][0][2], (1, 4))
            path.write_text(json.dumps({"chapters":[{"number":1,"title":"Example","sources":[{"id":"f01","pages":[4,1]}]}]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                chapter_map.load_chapter_map(path)

    def test_failed_browser_does_not_accept_stale_pdf(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIR) as tmp:
            html = pathlib.Path(tmp) / "note.html"
            output = pathlib.Path(tmp) / "old.pdf"
            html.write_text("<p>test</p>", encoding="utf-8")
            output.write_bytes(b"old")
            result = mock.Mock(returncode=1, stderr=b"failed", stdout=b"")
            with mock.patch.object(render.subprocess, "run", return_value=result):
                with self.assertRaises(RuntimeError):
                    render.html_to_pdf(html, output, "browser")
            self.assertEqual(output.read_bytes(), b"old")


if __name__ == "__main__":
    unittest.main()
