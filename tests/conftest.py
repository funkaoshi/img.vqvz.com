"""Fake Flickr API served through respx, so tests never touch the network."""

from __future__ import annotations

import re

import httpx
import pytest
import respx

from vqvz import create_app
from vqvz.cache import CachedFlickr
from vqvz.flickr import API_URL, FlickrClient

NSID = "12345678@N00"
SHIMA_SET = "72157619603386788"  # the curated "blansdowne" set in sets.yml


def photo_row(i: int, title: str | None = None) -> dict:
    """Even rows are newer 3:2 landscapes with 1600/2048 sizes; odd rows are
    older 2:3 portraits that stop at Large (1024), like pre-2012 uploads."""
    base = f"https://live.staticflickr.com/65535/{1000 + i}_abc"
    row = {
        "id": str(1000 + i), "owner": NSID, "secret": "abc", "server": "65535",
        "title": f"Photo {i}" if title is None else title,
        "datetaken": "2009-12-17 10:00:00", "pathalias": "funkaoshi",
        "ownername": "funkaoshi",
    }
    if i % 2 == 0:
        dims = {"z": (640, 427), "l": (1024, 683), "h": (1600, 1067), "k": (2048, 1365)}
    else:
        dims = {"z": (427, 640), "l": (683, 1024)}
    for s, (w, h) in dims.items():
        row |= {f"url_{s}": f"{base}_{s}.jpg", f"width_{s}": w, f"height_{s}": h}
    row["url_l"] = f"{base}_b.jpg"  # Flickr's Large URLs end in _b
    return row


def fail(code: int, message: str) -> httpx.Response:
    return httpx.Response(200, json={"stat": "fail", "code": code, "message": message})


class FakeFlickr:
    """Dispatches on the `method` query param, like the real REST endpoint."""

    def __init__(self, total_pages: int = 3):
        self.total_pages = total_pages
        self.calls: list[dict] = []
        self.fail_with: tuple[int, str] | None = None
        self.photo_title = "Shima"
        self.tagged: dict[str, int] = {"vqvz:set=shima": 2}
        # Groups by NSID, and URL name -> NSID for flickr.urls.lookupGroup.
        self.groups = {"755579@N24": "Photographs on the Brain"}
        self.group_aliases = {"photographsonthebrain": "755579@N24"}

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
        elif m == "flickr.groups.getInfo":
            if q["group_id"] not in self.groups:
                return fail(1, "Group not found")
            body = {"group": {"id": q["group_id"], "name": {"_content": self.groups[q["group_id"]]}}}
        elif m == "flickr.urls.lookupGroup":
            alias = q["url"].rstrip("/").rsplit("/", 1)[-1]
            if alias not in self.group_aliases:
                return fail(1, "Group not found")
            nsid = self.group_aliases[alias]
            body = {"group": {"id": nsid, "groupname": {"_content": self.groups[nsid]}}}
        elif m == "flickr.groups.pools.getPhotos":
            if q["group_id"] not in self.groups:
                return fail(1, "Group not found")
            body = {"photos": self.page_block(page, per_page, 2)}
        elif m == "flickr.favorites.getPublicList":
            body = {"photos": self.page_block(page, per_page, 1)}
        elif m == "flickr.photos.getInfo":
            body = {"photo": {"id": q["photo_id"], "title": {"_content": self.photo_title},
                              "dates": {"taken": "2009-12-18 12:00:00"},
                              "owner": {"nsid": NSID, "path_alias": "funkaoshi"},
                              "urls": {"url": [{"type": "photopage",
                                                "_content": f"https://www.flickr.com/photos/funkaoshi/{q['photo_id']}/"}]}}}
        elif m == "flickr.photos.getSizes":
            body = {"sizes": {"size": [
                {"label": "Medium", "source": "https://live.staticflickr.com/1/x.jpg", "width": 500, "height": 333},
                {"label": "Large", "source": "https://live.staticflickr.com/1/x_b.jpg", "width": "1024", "height": "683"},
                {"label": "Large 1600", "source": "https://live.staticflickr.com/1/x_h.jpg", "width": 1600, "height": 1067}]}}
        else:
            return fail(112, "Method not found")
        return httpx.Response(200, json={"stat": "ok", **body})


@pytest.fixture
def fake():
    fake = FakeFlickr()
    with respx.mock(assert_all_called=False) as router:
        router.get(API_URL).mock(side_effect=fake)
        yield fake


def make_app(site: str):
    from vqvz import gv, img
    sizes = {"img": img.IMAGE_SIZES, "gv": gv.IMAGE_SIZES}[site]
    flickr = CachedFlickr(FlickrClient("test-key", http=httpx.Client(), sizes=sizes))
    return create_app({"TESTING": True, "FLICKR_API_KEY": "test-key", "ANALYTICS_ID": ""},
                      flickr=flickr, site=site)


@pytest.fixture
def app(fake):
    return make_app("img")


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def gv_client(fake):
    return make_app("gv").test_client()


def meta(html, prop):
    m = re.search(rf'<meta (?:property|name)="{re.escape(prop)}" content="([^"]*)"', html)
    return m and m.group(1)
