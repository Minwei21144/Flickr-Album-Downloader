import unittest
import tempfile
import threading
import time
from pathlib import Path

import flickr_album_downloader as downloader
from app_metadata import APP_USER_AGENT, APP_VERSION
from flickr_album_downloader import (
    COMMON_RESOLUTION_OPTIONS,
    AlbumData,
    SizeItem,
    PhotoItem,
    build_resolution_options,
    choose_size,
    conflict_options_for_language,
    download_interval_for_workers,
    download_prepared_album_to_folder,
    extension_from_url,
    find_album_ref_in_text,
    parse_html_cover_url,
    parse_html_photo_cards,
    parse_album_url,
    photoset_cover_url,
    resolution_options_for_language,
    sanitize_filename,
    sanitize_folder_name,
    sizes_from_photo_extra,
    unique_filename,
    video_sizes_from_get_sizes,
    tr,
)
from update_checker import is_newer_version, result_from_release_payload, version_sort_key


class DownloaderCoreTests(unittest.TestCase):
    def test_version_metadata_is_used(self):
        self.assertRegex(APP_VERSION, r"^\d+\.\d+\.\d+$")
        self.assertEqual(downloader.USER_AGENT, APP_USER_AGENT)

    def test_release_version_comparison(self):
        self.assertEqual(version_sort_key("v1.0.0"), (1,))
        self.assertFalse(is_newer_version("v1.0.0", "1.0.0"))
        self.assertTrue(is_newer_version("v1.1.0", "1.0.9"))
        self.assertFalse(is_newer_version("bad-version", "1.0.0"))

    def test_release_payload_result_marks_update(self):
        result = result_from_release_payload(
            {"tag_name": "v1.2.0", "html_url": "https://example.test/releases/v1.2.0"},
            current_version="1.0.0",
        )
        self.assertTrue(result.is_update_available)
        self.assertEqual(result.latest_version, "1.2.0")
        self.assertEqual(result.release_url, "https://example.test/releases/v1.2.0")

    def test_parse_album_url_with_alias(self):
        parsed = parse_album_url("https://www.flickr.com/photos/example-user/albums/72177720300000000/")
        self.assertEqual(parsed.user_token, "example-user")
        self.assertEqual(parsed.photoset_id, "72177720300000000")

    def test_parse_album_url_with_old_sets_path(self):
        parsed = parse_album_url("www.flickr.com/photos/12345678@N00/sets/72157600000000000")
        self.assertEqual(parsed.user_token, "12345678@N00")
        self.assertEqual(parsed.photoset_id, "72157600000000000")

    def test_find_album_ref_in_share_page_text(self):
        parsed = find_album_ref_in_text('window.location="https://www.flickr.com/photos/midog/albums/72177720300000000/"')
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.user_token, "midog")
        self.assertEqual(parsed.photoset_id, "72177720300000000")

    def test_find_album_ref_from_model_export(self):
        parsed = find_album_ref_in_text('"albumId":"72177720300000000","nsid":"12345678@N00"')
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.user_token, "12345678@N00")
        self.assertEqual(parsed.photoset_id, "72177720300000000")

    def test_choose_numeric_size_prefers_largest_not_over_target(self):
        sizes = [
            SizeItem("Medium 800", 800, 600, "https://example.test/800.jpg"),
            SizeItem("Large", 1024, 768, "https://example.test/1024.jpg"),
            SizeItem("Large 2048", 2048, 1536, "https://example.test/2048.jpg"),
        ]
        selected = choose_size(sizes, "1600", fallback=True)
        self.assertEqual(selected.label, "Large")

    def test_choose_best_prefers_original_when_available(self):
        sizes = [
            SizeItem("Large 2048", 2048, 1536, "https://example.test/2048.jpg"),
            SizeItem("Original", 3000, 2000, "https://example.test/original.jpg"),
        ]
        selected = choose_size(sizes, "best", fallback=True)
        self.assertEqual(selected.label, "Original")

    def test_build_resolution_options_from_actual_sizes(self):
        photos = [
            PhotoItem(
                "1",
                "photo",
                sizes=(
                    SizeItem("Large", 1024, 768, "https://example.test/1024.jpg"),
                    SizeItem("Original", 3000, 2000, "https://example.test/original.jpg"),
                ),
            ),
            PhotoItem("2", "photo2", sizes=(SizeItem("Large 2048", 2048, 1200, "https://example.test/2048.jpg"),)),
        ]
        self.assertEqual(
            build_resolution_options(photos),
            tuple(COMMON_RESOLUTION_OPTIONS),
            (("best", "最大可用"), ("original", "原始檔"), ("2048", "2048px"), ("1024", "1024px")),
        )

    def test_english_language_options_are_available(self):
        self.assertEqual(resolution_options_for_language("en")[0], ("original", "Original / largest available"))
        self.assertEqual(conflict_options_for_language("en")[0], ("resume", "Resume / skip existing photos"))
        self.assertEqual(tr("btn_start", "en"), "Start download")

    def test_download_interval_scales_with_workers(self):
        self.assertEqual(download_interval_for_workers(1), 6.0)
        self.assertEqual(download_interval_for_workers(4), 1.5)
        self.assertEqual(download_interval_for_workers(99), 0.25)

    def test_album_preview_prefers_cover_url(self):
        album = AlbumData(
            title="album",
            canonical_url="https://example.test/album",
            photos=(PhotoItem("1", "first", thumbnail_url="https://example.test/first.jpg"),),
            resolution_options=tuple(COMMON_RESOLUTION_OPTIONS),
            cover_url="https://example.test/cover.jpg",
        )
        self.assertEqual(album.preview_url, "https://example.test/cover.jpg")

    def test_photoset_cover_url_from_api_info(self):
        self.assertEqual(
            photoset_cover_url({"primary": "123", "secret": "abc", "server": "456"}),
            "https://live.staticflickr.com/456/123_abc_q.jpg",
        )

    def test_parse_html_cover_url(self):
        page = '<meta property="og:image" content="//live.staticflickr.com/1/2_q.jpg">'
        self.assertEqual(parse_html_cover_url(page), "https://live.staticflickr.com/1/2_q.jpg")

    def test_download_workers_pass_scaled_interval_and_overlap(self):
        original_download_to_file = downloader.download_to_file
        intervals: list[float] = []
        active = 0
        max_active = 0
        lock = threading.Lock()

        def fake_download(source_url, target_path, cancel_event=None, pause_event=None, log=None, min_interval=6.0):
            nonlocal active, max_active
            intervals.append(min_interval)
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.05)
            Path(target_path).write_bytes(b"image")
            with lock:
                active -= 1
            return "image/jpeg"

        downloader.download_to_file = fake_download
        try:
            album = AlbumData(
                title="parallel-test",
                canonical_url="https://example.test/album",
                photos=tuple(
                    PhotoItem(str(index), f"photo-{index}", sizes=(SizeItem("Original", 100, 100, f"https://example.test/{index}.jpg"),))
                    for index in range(4)
                ),
                resolution_options=tuple(COMMON_RESOLUTION_OPTIONS),
            )
            with tempfile.TemporaryDirectory() as tmpdir:
                download_prepared_album_to_folder(album, Path(tmpdir), "original", workers=4)
        finally:
            downloader.download_to_file = original_download_to_file

        self.assertEqual(intervals, [1.5, 1.5, 1.5, 1.5])
        self.assertGreater(max_active, 1)

    def test_download_worker_getter_can_increase_during_run(self):
        original_download_to_file = downloader.download_to_file
        worker_box = {"value": 1}
        intervals: list[float] = []
        active = 0
        max_active = 0
        lock = threading.Lock()

        def fake_download(source_url, target_path, cancel_event=None, pause_event=None, log=None, min_interval=6.0):
            nonlocal active, max_active
            intervals.append(min_interval)
            with lock:
                active += 1
                max_active = max(max_active, active)
            if source_url.endswith("/0.jpg"):
                threading.Timer(0.05, lambda: worker_box.update(value=4)).start()
                time.sleep(0.35)
            else:
                time.sleep(0.1)
            Path(target_path).write_bytes(b"image")
            with lock:
                active -= 1
            return "image/jpeg"

        downloader.download_to_file = fake_download
        try:
            album = AlbumData(
                title="dynamic-parallel-test",
                canonical_url="https://example.test/album",
                photos=tuple(
                    PhotoItem(str(index), f"photo-{index}", sizes=(SizeItem("Original", 100, 100, f"https://example.test/{index}.jpg"),))
                    for index in range(4)
                ),
                resolution_options=tuple(COMMON_RESOLUTION_OPTIONS),
            )
            with tempfile.TemporaryDirectory() as tmpdir:
                download_prepared_album_to_folder(
                    album,
                    Path(tmpdir),
                    "original",
                    workers=1,
                    worker_count_getter=lambda: worker_box["value"],
                )
        finally:
            downloader.download_to_file = original_download_to_file

        self.assertIn(6.0, intervals)
        self.assertIn(1.5, intervals)
        self.assertGreater(max_active, 1)

    def test_download_removes_manifest_file(self):
        original_download_to_file = downloader.download_to_file

        def fake_download(source_url, target_path, cancel_event=None, pause_event=None, log=None, min_interval=6.0):
            Path(target_path).write_bytes(b"image")
            return "image/jpeg"

        downloader.download_to_file = fake_download
        try:
            album = AlbumData(
                title="manifest-test",
                canonical_url="https://example.test/album",
                photos=(PhotoItem("1", "photo", sizes=(SizeItem("Original", 100, 100, "https://example.test/1.jpg"),)),),
                resolution_options=tuple(COMMON_RESOLUTION_OPTIONS),
            )
            with tempfile.TemporaryDirectory() as tmpdir:
                album_dir = Path(tmpdir) / "manifest-test"
                album_dir.mkdir()
                manifest = album_dir / ".flickr_download_manifest.json"
                manifest.write_text("old", encoding="utf-8")
                result = download_prepared_album_to_folder(album, Path(tmpdir), "original", workers=1)
                self.assertTrue(result.samefile(album_dir), f"{result} != {album_dir}")
                self.assertFalse(manifest.exists())
        finally:
            downloader.download_to_file = original_download_to_file

    def test_video_extra_original_stays_image(self):
        sizes = sizes_from_photo_extra(
            {
                "media": "video",
                "originalformat": "mp4",
                "url_o": "https://live.staticflickr.com/example_o.jpg",
                "width_o": "1920",
                "height_o": "1080",
            }
        )
        self.assertEqual(sizes[0].label, "Original")
        self.assertIsNone(sizes[0].preferred_extension)

    def test_video_play_sizes_use_mp4_extension(self):
        sizes = video_sizes_from_get_sizes(
            [
                SizeItem("Original", 1920, 1080, "https://live.staticflickr.com/example_o.jpg"),
                SizeItem("1080p", 1920, 1080, "https://www.flickr.com/photos/u/1/play/1080p/secret/"),
                SizeItem("720p", 1280, 720, "https://www.flickr.com/photos/u/1/play/720p/secret/"),
            ]
        )
        self.assertEqual([size.label for size in sizes], ["1080p", "720p"])
        self.assertTrue(all(size.preferred_extension == ".mp4" for size in sizes))

    def test_parse_html_photo_cards(self):
        page = '''
        <div class="view photo-card-view requiredToShowOnServer"
          data-view-signature="photo-card-view__id_164666925__model_1">
          <img src="//live.staticflickr.com/51/164666925_43d21c3752_h.jpg" width="1600" height="1067">
          <a class="title" href="/photos/bees/164666925/in/album-721">Laura / Helvetica Neue</a>
        </div><div class="view pagination-view"></div>
        '''
        photos = parse_html_photo_cards(page)
        self.assertEqual(len(photos), 1)
        self.assertEqual(photos[0].photo_id, "164666925")
        self.assertEqual(photos[0].title, "Laura / Helvetica Neue")
        self.assertEqual(photos[0].sizes[0].longest_edge, 1600)

    def test_sanitize_filename_preserves_readable_title(self):
        filename = sanitize_filename('旅遊: 東京 / Day 1?', ".jpg")
        self.assertEqual(filename, "旅遊_ 東京 _ Day 1_.jpg")

    def test_sanitize_zip_filename_does_not_keep_image_suffix(self):
        filename = sanitize_filename("album.jpg", ".zip", preserve_image_suffix=False)
        self.assertEqual(filename, "album.jpg.zip")

    def test_sanitize_folder_name(self):
        folder = sanitize_folder_name('旅行: 東京 / Day 1?')
        self.assertEqual(folder, "旅行_ 東京 _ Day 1_")

    def test_extension_from_content_type_uses_jpg(self):
        self.assertEqual(extension_from_url("https://example.test/photo", "image/jpeg"), ".jpg")

    def test_unique_filename_adds_counter(self):
        used = set()
        self.assertEqual(unique_filename("photo.jpg", used), "photo.jpg")
        self.assertEqual(unique_filename("photo.jpg", used), "photo (2).jpg")


if __name__ == "__main__":
    unittest.main()
