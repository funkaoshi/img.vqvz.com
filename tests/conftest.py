"""Fake Flickr API served through respx, so tests never touch the network."""

from __future__ import annotations

import httpx
import pytest
import respx

from vqvz import create_app
from vqvz.cache import CachedFlickr
from vqvz.flickr import API_URL, FlickrClient

NSID = "12345678@N00"
SHIMA_SET = "72157619603386788"  # the curated "blansdowne" set in sets.yml


def photo_row(i: int, title: str | None = None) -> dict:
    return {
        "id": str(1000 + i), "owner": NSID, "secret": "abc", "server": "65535",
        "title": f"Photo {i}" if title is None else title,
        "datetaken": "2009-12-17 10:00:00", "pathalias": "funkaoshi",
        "url_l": f"https://live.staticflickr.com/65535/{1000 + i}_abc_b.jpg",
    }


class FakeFlickr:
    """Dispatches on the `method` query param, like the real REST endpoint."""

    def __init__(self, total_pages: int = 3):
        self.total_pages = total_pages
        self.calls: list[dict] = []
        self.fail_with: tuple[int, str] | None = None
        self.photo_title = "Shima"
        self.tagged: dict[str, int] = {"vqvz:set=shima": 2}

    def page_block(self, page: int, per_page: int, pages: int, **extra) -> dict:
        start = (page - 1) * per_page
        rows = [photo_row(start + i) for i in range(per_page)] if page <= pages else []
        return {"page": page, "pages": pages, "perpage": per_page, "photo": rows, **extra}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        q = dict(request.url.params)
        self.calls.append(q)
        if self.fail_with:
            code, msg = self.fail_with
            return httpx.Response(200, json={"stat": "fail", "code": code, "message": msg})
        m = q["method"]
        page, per_page = int(q.get("page", 1)), int(q.get("per_page", 10))
        if m == "flickr.people.findByUsername":
            body = {"user": {"nsid": NSID}}
        elif m == "flickr.people.getInfo":
            body = {"person": {"username": {"_content": "funkaoshi"},
                               "realname": {"_content": "Ramanan Sivaranjan"},
                               "profileurl": {"_content": "https://www.flickr.com/people/funkaoshi/"}}}
        elif m == "flickr.photos.search":
            if "machine_tags" in q:
                n = self.tagged.get(q["machine_tags"], 0)
                rows = [photo_row(i) for i in range(n)]
                body = {"photos": {"page": 1, "pages": 1 if n else 0, "photo": rows}}
            else:
                body = {"photos": self.page_block(page, per_page, self.total_pages)}
        elif m == "flickr.photosets.getPhotos":
            body = {"photoset": self.page_block(page, per_page, 2, owner=NSID,
                                                title=f"Set {q['photoset_id']}")}
        elif m == "flickr.photos.getInfo":
            body = {"photo": {"id": q["photo_id"], "title": {"_content": self.photo_title},
                              "dates": {"taken": "2009-12-18 12:00:00"},
                              "owner": {"nsid": NSID, "path_alias": "funkaoshi"},
                              "urls": {"url": [{"type": "photopage",
                                                "_content": f"https://www.flickr.com/photos/funkaoshi/{q['photo_id']}/"}]}}}
        elif m == "flickr.photos.getSizes":
            body = {"sizes": {"size": [
                {"label": "Medium", "source": "https://live.staticflickr.com/1/x.jpg"},
                {"label": "Large", "source": "https://live.staticflickr.com/1/x_b.jpg"}]}}
        else:
            return httpx.Response(200, json={"stat": "fail", "code": 112, "message": "Method not found"})
        return httpx.Response(200, json={"stat": "ok", **body})


@pytest.fixture
def fake():
    fake = FakeFlickr()
    with respx.mock(assert_all_called=False) as router:
        router.get(API_URL).mock(side_effect=fake)
        yield fake


@pytest.fixture
def app(fake):
    flickr = CachedFlickr(FlickrClient("test-key", http=httpx.Client()))
    return create_app({"TESTING": True, "FLICKR_API_KEY": "test-key", "ANALYTICS_ID": ""}, flickr=flickr)


@pytest.fixture
def client(app):
    return app.test_client()
