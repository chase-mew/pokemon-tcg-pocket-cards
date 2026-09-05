"""Tests for the download stage and the CLI plumbing around it.

No network: the shared ``SESSION`` is replaced with a stub that serves a
generated in-memory image.
"""
import io

import pytest
from PIL import Image

import add_expansion
import downloader
import set_writer
from add_expansion import resolve_set_range
from constants import EXPANSIONS_SCHEMA_PATH
from downloader import download_images, download_pack_images
from set_writer import validate_schema
from tests.utils import _load
from transformer import strip_source_urls


def png_bytes(size=(64, 64)):
    """A noisy PNG, so it clears the 500-byte "real artwork" threshold."""
    image = Image.new("RGB", size)
    image.putdata([((x * 7) % 256, (y * 13) % 256, (x * y) % 256)
                   for y in range(size[1]) for x in range(size[0])])
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


class StubResponse:
    def __init__(self, content=b"", status_code=200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class StubSession:
    """Records every URL it is asked for and serves a valid image."""

    def __init__(self, content=None, status_code=200):
        self.content = png_bytes() if content is None else content
        self.status_code = status_code
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        return StubResponse(self.content, self.status_code)


@pytest.fixture
def image_dirs(tmp_path, monkeypatch):
    dirs = {}
    for name in ("WEBP_CARDS_DIR", "PNG_CARDS_DIR", "WEBP_PACKS_DIR", "PNG_PACKS_DIR"):
        path = tmp_path / name.lower()
        path.mkdir()
        dirs[name] = path
        monkeypatch.setattr(downloader, name, str(path))
    monkeypatch.setattr(downloader.time, "sleep", lambda *_: None)
    return dirs


@pytest.fixture
def session(monkeypatch):
    stub = StubSession()
    monkeypatch.setattr(downloader, "SESSION", stub)
    return stub


def card(card_id="a1-001", url="https://limitlesstcg.com/pocket/a1/1.webp"):
    return {"id": card_id, "source_url": url}


# ---------------------------------------------------------------------------
# Card images
# ---------------------------------------------------------------------------

class TestDownloadImages:
    def test_writes_both_formats_named_after_the_card_number(self, image_dirs, session):
        download_images([card("a1-007")], "a1")
        assert (image_dirs["WEBP_CARDS_DIR"] / "a1" / "007.webp").exists()
        assert (image_dirs["PNG_CARDS_DIR"] / "a1" / "007.png").exists()

    def test_source_url_survives_the_download(self, image_dirs, session):
        """Downloading is not the same job as stripping; the orchestrator strips."""
        cards = [{"id": "a1-001", "source_url": "https://limitlesstcg.com/a.webp"}]
        download_images(cards, "a1")
        assert cards[0]["source_url"] == "https://limitlesstcg.com/a.webp"

    def test_existing_files_are_not_downloaded_again(self, image_dirs, session):
        download_images([card()], "a1")
        download_images([card()], "a1")
        assert len(session.urls) == 1

    @pytest.mark.parametrize("url", [
        None,
        "",
        "http://limitlesstcg.com/a.webp",          # not https
        "https://evil.example.com/a.webp",         # wrong host
        "https://notlimitlesstcg.com/a.webp",      # suffix confusion
        "https://limitlesstcg.com.evil.dev/a.webp",
    ])
    def test_untrusted_or_missing_urls_are_rejected(self, image_dirs, session, url):
        with pytest.raises(RuntimeError, match="source_url"):
            download_images([card(url=url)], "a1")

    def test_subdomains_of_the_source_host_are_accepted(self, image_dirs, session):
        download_images([card(url="https://cdn.limitlesstcg.com/a.webp")], "a1")
        assert session.urls == ["https://cdn.limitlesstcg.com/a.webp"]

    def test_a_failed_download_stops_the_batch(self, image_dirs, monkeypatch):
        monkeypatch.setattr(downloader, "SESSION", StubSession(status_code=500))
        with pytest.raises(RuntimeError, match="Critical failure"):
            download_images([card()], "a1")

    def test_undecodable_content_stops_the_batch(self, image_dirs, monkeypatch):
        monkeypatch.setattr(downloader, "SESSION", StubSession(content=b"not an image"))
        with pytest.raises(RuntimeError, match="Critical failure"):
            download_images([card()], "a1")


# ---------------------------------------------------------------------------
# Pack images
# ---------------------------------------------------------------------------

class TestDownloadPackImages:
    def pack(self, pack_id="a1-mewtwo", name="Mewtwo", image="https://example/x.webp"):
        return {"id": pack_id, "name": name, "image": image, "image_png": image}

    def test_writes_both_formats(self, image_dirs, session):
        download_pack_images("Genetic Apex", [self.pack()])
        assert (image_dirs["WEBP_PACKS_DIR"] / "a1-mewtwo.webp").exists()
        assert (image_dirs["PNG_PACKS_DIR"] / "a1-mewtwo.png").exists()

    def test_url_is_built_from_the_expansion_and_pack_slugs(self, image_dirs, session):
        download_pack_images("Genetic Apex", [self.pack(name="Ho-Oh")])
        assert session.urls[0].endswith("/geneticapex/ho-oh.jpg")

    def test_promo_packs_without_artwork_are_skipped(self, image_dirs, session):
        """update_expansions sets image=None for promos; nothing should be fetched."""
        download_pack_images("Promo-A", [self.pack("pa-promov1", "Promo V1", image=None)])
        assert session.urls == []
        assert not list(image_dirs["WEBP_PACKS_DIR"].iterdir())

    def test_tiny_responses_are_treated_as_missing_artwork(self, image_dirs, monkeypatch):
        monkeypatch.setattr(downloader, "SESSION", StubSession(content=b"x" * 100))
        download_pack_images("Genetic Apex", [self.pack()])
        assert not list(image_dirs["WEBP_PACKS_DIR"].iterdir())

    def test_a_broken_pack_does_not_raise(self, image_dirs, monkeypatch):
        monkeypatch.setattr(downloader, "SESSION", StubSession(status_code=404))
        download_pack_images("Genetic Apex", [self.pack()])

    def test_existing_files_are_not_downloaded_again(self, image_dirs, session):
        download_pack_images("Genetic Apex", [self.pack()])
        download_pack_images("Genetic Apex", [self.pack()])
        assert len(session.urls) == 1


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------

class TestResolveSetRange:
    def test_single_code_is_normalised(self):
        assert resolve_set_range("pa") == ["P-A"]
        assert resolve_set_range("b2b") == ["B2B"]

    def test_range_is_expanded_oldest_first(self, monkeypatch):
        monkeypatch.setattr(add_expansion, "get_all_set_codes",
                            lambda: ["B1", "A2", "A1"])  # index order: newest first
        assert resolve_set_range("a1->b1") == ["A1", "A2", "B1"]

    def test_reversed_range_still_resolves(self, monkeypatch):
        monkeypatch.setattr(add_expansion, "get_all_set_codes", lambda: ["B1", "A2", "A1"])
        assert resolve_set_range("b1->a1") == ["A1", "A2", "B1"]

    def test_unknown_set_exits(self, monkeypatch):
        monkeypatch.setattr(add_expansion, "get_all_set_codes", lambda: ["A1"])
        with pytest.raises(SystemExit):
            resolve_set_range("a1->zz")


class TestValidateSchema:
    def test_valid_cards_pass(self, cards):
        validate_schema(cards[:5])

    def test_a_leaked_source_url_is_rejected(self, cards):
        with pytest.raises(ValueError, match="Schema violation"):
            validate_schema([{**cards[0], "source_url": "https://example.invalid/x.webp"}])

    def test_a_missing_field_is_rejected(self, cards):
        broken = {k: v for k, v in cards[0].items() if k != "deckBuilderNr"}
        with pytest.raises(ValueError, match="Schema violation"):
            validate_schema([broken])

    def test_a_wrongly_typed_field_is_rejected(self, cards):
        with pytest.raises(ValueError, match="Schema violation"):
            validate_schema([{**cards[0], "deckBuilderNr": "12"}])

    def test_a_missing_schema_file_raises(self, monkeypatch, tmp_path):
        monkeypatch.setattr(set_writer, "CARDS_SCHEMA_PATH", str(tmp_path / "nope.json"))
        with pytest.raises(FileNotFoundError):
            validate_schema([])

    def test_a_valid_expansion_index_passes(self, expansions):
        validate_schema(expansions, EXPANSIONS_SCHEMA_PATH, "expansions")

    def test_a_broken_expansion_index_is_rejected(self, expansions):
        broken = [{**expansions[0], "total_cards": "many"}]
        with pytest.raises(ValueError, match="expansions"):
            validate_schema(broken, EXPANSIONS_SCHEMA_PATH, "expansions")

    @pytest.mark.parametrize("path_name, label", [
        ("V4_CARDS_SCHEMA_PATH", "v4 cards"),
        ("V4_EXPANSIONS_SCHEMA_PATH", "v4 expansions"),
    ])
    def test_the_published_v4_files_validate(self, path_name, label):
        """The v4 schemas generate published .d.ts types; nothing checked the data."""
        import constants
        schema_path = getattr(constants, path_name)
        data_path = schema_path.replace(".schema.json", ".json")
        validate_schema(_load(data_path), schema_path, label)


class TestStripSourceUrls:
    def test_removes_the_key_from_every_card(self):
        cards = [{"id": "a1-001", "source_url": "https://x/1.webp"}, {"id": "a1-002"}]
        strip_source_urls(cards)
        assert cards == [{"id": "a1-001"}, {"id": "a1-002"}]


class TestLimitlessHostAllowlist:
    @pytest.mark.parametrize("host, accepted", [
        ("limitlesstcg.com", True),
        ("cdn.limitlesstcg.com", True),
        ("limitlesstcg.nyc3.cdn.digitaloceanspaces.com", True),
        ("limitlesstcg.tor1.cdn.digitaloceanspaces.com", True),
        ("limitlesstcg.com.evil.com", False),
        ("evil-limitlesstcg.com", False),
        ("evil.limitlesstcg.nyc3.cdn.digitaloceanspaces.com", False),
        ("attacker.nyc3.cdn.digitaloceanspaces.com", False),
        ("limitlesstcg.nyc3.cdn.digitaloceanspaces.com.evil.com", False),
    ])
    def test_host_allowlist(self, host, accepted):
        from constants import LIMITLESS_HOST
        assert bool(LIMITLESS_HOST.match(host)) is accepted
