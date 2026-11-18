import httpx
import pytest
import respx

from vqvz.cache import CachedFlickr
from vqvz.flickr import API_URL, FlickrClient, FlickrError, Listing, Photo, clean_title


@pytest.mark.parametrize("raw,expected", [
    ("Shima", "Shima"), ("", "untitled"), (None, "untitled"), (".", "untitled"),
    ("IMG_1234", "untitled"), ("DSC_0042", "untitled"), ("  Birds  ", "Birds"),
    ("IMG_1234 at the beach", "IMG_1234 at the beach"),
])
def test_clean_title(raw, expected):
    assert clean_title(raw) == expected


def test_from_search_prefers_large_then_falls_back():
    base = {"id": "1", "secret": "s", "server": "9", "title": "t", "datetaken": "2010-01-02 03:04:05",
            "pathalias": "funkaoshi"}
    assert Photo.from_search({**base, "url_l": "L", "url_z": "Z"}).img_url == "L"
    assert Photo.from_search({**base, "url_z": "Z"}).img_url == "Z"
    p = Photo.from_search(base)
    assert p.img_url == "https://live.staticflickr.com/9/1_s_z.jpg"
    assert p.date_taken == "2010-01-02"
    assert p.page_url == "https://www.flickr.com/photos/funkaoshi/1/"


def test_from_search_uses_set_owner_when_row_has_none():
    p = Photo.from_search({"id": "1", "secret": "s", "server": "9", "title": "t"}, owner="99@N00")
    assert p.page_url == "https://www.flickr.com/photos/99@N00/1/"


def test_from_info_picks_large_else_medium():
    info = {"id": "7", "title": {"_content": "Shima"}, "dates": {"taken": "2009-12-18 12:00:00"},
            "owner": {"nsid": "n", "path_alias": "funkaoshi"}}
    sizes = [{"label": "Medium", "source": "M"}, {"label": "Large", "source": "L"}]
    assert Photo.from_info(info, sizes).img_url == "L"
    assert Photo.from_info(info, sizes[:1]).img_url == "M"
    assert Photo.from_info(info, sizes).page_url == "https://www.flickr.com/photos/funkaoshi/7/"


def listing(page, pages):
    return Listing("t", [], page, pages, lambda n: f"/p/{n}")


@pytest.mark.parametrize("page,pages,prev,next_,paginated", [
    (1, 1, None, None, False),
    (1, 3, None, "/p/2", True),
    (2, 3, "/p/1", "/p/3", True),
    (3, 3, "/p/2", None, True),
])
def test_listing_links(page, pages, prev, next_, paginated):
    lst = listing(page, pages)
    assert (lst.prev_url, lst.next_url, lst.paginated) == (prev, next_, paginated)


@respx.mock
def test_client_raises_on_flickr_failure():
    respx.get(API_URL).respond(json={"stat": "fail", "code": 1, "message": "Photo not found"})
    with pytest.raises(FlickrError) as exc:
        FlickrClient("k", http=httpx.Client()).photo("1")
    assert exc.value.not_found


@respx.mock
def test_client_wraps_transport_errors():
    respx.get(API_URL).mock(side_effect=httpx.ConnectError("down"))
    with pytest.raises(FlickrError) as exc:
        FlickrClient("k", http=httpx.Client()).search("u")
    assert exc.value.code == -1 and not exc.value.not_found


def test_cache_reuses_results_and_skips_errors():
    calls = []

    class Stub:
        def search(self, user, page=1):
            calls.append(page)
            if page == 99:
                raise FlickrError(-1, "boom")
            return page

    c = CachedFlickr(Stub())
    assert c.search("u", page=2) == 2 and c.search("u", page=2) == 2
    assert calls == [2]
    for _ in range(2):
        with pytest.raises(FlickrError):
            c.search("u", page=99)
    assert calls == [2, 99, 99]


@respx.mock
def test_error_messages_do_not_leak_api_key():
    respx.get(API_URL).respond(status_code=502)
    with pytest.raises(FlickrError) as exc:
        FlickrClient("secret-key", http=httpx.Client()).search("u")
    assert "secret-key" not in str(exc.value)
    assert exc.value.__cause__ is None and exc.value.__suppress_context__


@respx.mock
def test_requests_send_our_user_agent():
    # Flickr returns a 502 HTML page to httpx's default User-Agent.
    from vqvz.flickr import USER_AGENT
    route = respx.get(API_URL).respond(json={"stat": "ok", "user": {"nsid": "n"}})
    FlickrClient("k", http=httpx.Client()).call("flickr.people.findByUsername", username="x")
    assert route.calls.last.request.headers["User-Agent"] == USER_AGENT


def test_image_size_preference():
    from vqvz.flickr import MEDIUM_640
    row = {"id": "1", "secret": "s", "server": "9", "title": "t", "url_l": "L", "url_z": "Z",
           "ownername": "Someone", "pathalias": "someone"}
    assert Photo.from_search(row).img_url == "L"
    assert Photo.from_search(row, sizes=MEDIUM_640).img_url == "Z"
    p = Photo.from_search(row)
    assert (p.owner_name, p.owner_url) == ("Someone", "https://www.flickr.com/photos/someone/")


def test_config_per_site_and_env_override():
    from vqvz.config import from_env
    assert from_env("img", {})["PER_PAGE"] == 10
    assert from_env("gv", {})["PER_PAGE"] == 30
    assert from_env("gv", {"PER_PAGE": "12"})["PER_PAGE"] == 12
    with pytest.raises(ValueError):
        from_env("nope", {})


def test_search_row_dimensions_and_srcset():
    import conftest
    landscape, portrait = Photo.from_search(conftest.photo_row(0)), Photo.from_search(conftest.photo_row(1))
    assert landscape.img_url.endswith("_b.jpg")           # still Large, for og:image
    assert (landscape.width, landscape.height) == (1024, 683)
    assert round(landscape.aspect, 2) == 1.5 and round(portrait.aspect, 2) == 0.67
    assert [w for _, w in landscape.sources] == [640, 1024, 1600, 2048]
    assert landscape.srcset.endswith("_k.jpg 2048w")
    assert [w for _, w in portrait.sources] == [427, 683]  # older photo: stops at Large
    assert (landscape.max_width, portrait.max_width) == (2048, 683)


def test_search_row_without_dimensions_falls_back():
    p = Photo.from_search({"id": "1", "secret": "s", "server": "9", "title": "t"})
    assert (p.width, p.height, p.aspect, p.srcset, p.max_width) == (0, 0, 1.5, "", 0)


def test_from_info_dimensions_and_srcset():
    info = {"id": "7", "title": {"_content": "Shima"}, "owner": {"nsid": "n"}}
    sizes = [{"label": "Medium 640", "source": "M", "width": "640", "height": "427"},
             {"label": "Large", "source": "L", "width": 1024, "height": 683},
             {"label": "Large 2048", "source": "K", "width": 2048, "height": 1365},
             {"label": "Original", "source": "O", "width": 4000, "height": 2667}]
    p = Photo.from_info(info, sizes)
    assert (p.img_url, p.width, p.height) == ("L", 1024, 683)
    assert p.srcset == "M 640w, L 1024w, K 2048w"      # Original isn't offered
