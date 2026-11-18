"""Site-agnostic Flickr access: a thin REST client plus the Photo/Listing models.

Shared by img.vqvz.com (one person's photostream) and gv.vqvz.com (group
pools and favourites); nothing in here knows about either site.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

import httpx

API_URL = "https://api.flickr.com/services/rest/"
# Flickr's front end answers httpx's default "python-httpx/x.y" User-Agent
# with an HTML 502 page, so every request identifies itself explicitly.
USER_AGENT = "vqvz/2.0 (+https://img.vqvz.com)"
EXTRAS = "date_taken,url_z,url_c,url_l,url_h,url_k,path_alias,owner_name"

# Which image size to show, best first. Large suits a single-column photoblog;
# a group viewer wants 640px images (and other people's photos often have no
# Large size at all). If none are present we build the 640px URL ourselves.
LARGE_FIRST = ("url_l", "url_c", "url_z")
MEDIUM_640 = ("url_z",)

# Every size offered to the browser via srcset, smallest first: 640, 800,
# 1024, 1600 and 2048px on the long edge. Flickr returns width_x/height_x with
# each url_x. Photos uploaded before ~2012 stop at 1024 (url_l).
SRCSET_SIZES = ("url_z", "url_c", "url_l", "url_h", "url_k")
# The same sizes as photos.getSizes labels them.
SRCSET_LABELS = ("Medium 640", "Medium 800", "Large", "Large 1600", "Large 2048")

_GROUP_NSID = re.compile(r"^\d+@N\d+$")

# Flickr error codes that mean "the thing you asked for isn't there".
NOT_FOUND_CODES = {1, 2}

_UNTITLED = re.compile(r"^(?:\.|IMG_\d+|DSC_?\d+|DSCF\d+|P\d+)?$", re.IGNORECASE)


class FlickrError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(f"Flickr error {code}: {message}")
        self.code = code
        self.message = message

    @property
    def not_found(self) -> bool:
        return self.code in NOT_FOUND_CODES


def clean_title(title: str | None) -> str:
    title = (title or "").strip()
    return "untitled" if _UNTITLED.match(title) else title


def page_url(owner: str, photo_id: str) -> str:
    return f"https://www.flickr.com/photos/{owner}/{photo_id}/"


def photostream_url(owner: str) -> str:
    return f"https://www.flickr.com/photos/{owner}/"


def is_group_nsid(ref: str) -> bool:
    return bool(_GROUP_NSID.match(ref))


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


@dataclass(frozen=True)
class Photo:
    id: str
    title: str
    date_taken: str  # YYYY-MM-DD
    img_url: str
    page_url: str
    owner_name: str = ""
    owner_url: str = ""
    width: int = 0   # of img_url; 0 when Flickr didn't say
    height: int = 0
    sources: tuple[tuple[str, int], ...] = ()  # (url, width) for srcset, smallest first

    @property
    def aspect(self) -> float:
        """Width / height; 1.5 (3:2) when unknown."""
        return self.width / self.height if self.width and self.height else 1.5

    @property
    def max_width(self) -> int:
        """Width of the largest size Flickr offers; 0 when unknown.
        Photos are never displayed wider than this (no upscaling)."""
        return max([w for _, w in self.sources] + [self.width])

    @property
    def srcset(self) -> str:
        return ", ".join(f"{url} {w}w" for url, w in self.sources)

    @classmethod
    def from_search(cls, p: dict[str, Any], owner: str | None = None,
                    sizes: tuple[str, ...] = LARGE_FIRST) -> "Photo":
        """Build from a photos.search / photosets.getPhotos / pool result row."""
        key = next((k for k in sizes if p.get(k)), None)
        if key:
            img, suffix = p[key], key[len("url_"):]
            width, height = _int(p.get(f"width_{suffix}")), _int(p.get(f"height_{suffix}"))
        else:  # construct the 640px URL ourselves; size unknown
            img = f"https://live.staticflickr.com/{p['server']}/{p['id']}_{p['secret']}_z.jpg"
            width = height = 0
        sources = tuple(
            (p[k], _int(p.get(f"width_{k[4:]}")))
            for k in SRCSET_SIZES if p.get(k) and _int(p.get(f"width_{k[4:]}"))
        )
        who = p.get("pathalias") or p.get("owner") or owner or ""
        return cls(
            id=str(p["id"]),
            title=clean_title(p.get("title")),
            date_taken=(p.get("datetaken") or "")[:10],
            img_url=img,
            page_url=page_url(who, p["id"]),
            owner_name=p.get("ownername") or "",
            owner_url=photostream_url(who) if who else "",
            width=width,
            height=height,
            sources=sources,
        )

    @classmethod
    def from_info(cls, info: dict[str, Any], sizes: list[dict[str, Any]]) -> "Photo":
        """Build from photos.getInfo + photos.getSizes."""
        by_label = {s["label"]: s for s in sizes}
        chosen = next(
            (by_label[k] for k in ("Large", "Medium 800", "Medium 640", "Medium") if k in by_label),
            sizes[-1] if sizes else {},
        )
        img = chosen.get("source", "")
        sources = tuple(
            (by_label[k]["source"], _int(by_label[k].get("width")))
            for k in SRCSET_LABELS if k in by_label and _int(by_label[k].get("width"))
        )
        owner = info.get("owner", {})
        url = next(
            (u["_content"] for u in info.get("urls", {}).get("url", []) if u.get("type") == "photopage"),
            page_url(owner.get("path_alias") or owner.get("nsid", ""), info["id"]),
        )
        who = owner.get("path_alias") or owner.get("nsid", "")
        return cls(
            id=str(info["id"]),
            title=clean_title(info.get("title", {}).get("_content")),
            date_taken=(info.get("dates", {}).get("taken") or "")[:10],
            img_url=img,
            page_url=url,
            owner_name=owner.get("username", ""),
            owner_url=photostream_url(who) if who else "",
            width=_int(chosen.get("width")),
            height=_int(chosen.get("height")),
            sources=sources,
        )


@dataclass(frozen=True)
class Listing:
    """One page of photos plus everything needed to render paging links.

    `url_for_page(n)` builds the URL of page n; it keeps routing out of here.
    """

    title: str
    photos: list[Photo]
    page: int
    pages: int
    url_for_page: Callable[[int], str] = field(repr=False, compare=False)

    @property
    def prev_url(self) -> str | None:
        return self.url_for_page(self.page - 1) if self.page > 1 else None

    @property
    def next_url(self) -> str | None:
        return self.url_for_page(self.page + 1) if self.page < self.pages else None

    @property
    def paginated(self) -> bool:
        return self.pages > 1


@dataclass(frozen=True)
class PhotoPage:
    """Raw result of a paged Flickr call, before it becomes a Listing."""

    photos: list[Photo]
    page: int
    pages: int
    title: str = ""


@dataclass(frozen=True)
class User:
    nsid: str
    username: str
    realname: str
    profile_url: str


@dataclass(frozen=True)
class Group:
    nsid: str
    name: str


class FlickrClient:
    """Read-only Flickr REST client. Only public, unauthenticated calls.

    `sizes` is the image size preference used for every photo list.
    """

    def __init__(self, api_key: str, http: httpx.Client | None = None,
                 sizes: tuple[str, ...] = LARGE_FIRST):
        self.api_key = api_key
        self.http = http or httpx.Client(timeout=10.0)
        self.sizes = sizes

    def call(self, method: str, **params: Any) -> dict[str, Any]:
        query = {
            "method": method,
            "api_key": self.api_key,
            "format": "json",
            "nojsoncallback": 1,
            **{k: v for k, v in params.items() if v is not None},
        }
        try:
            resp = self.http.get(API_URL, params=query, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            # str(e) includes the URL, which carries the API key; keep it out of logs.
            body = " ".join(e.response.text.split())[:200]
            raise FlickrError(-1, f"{method}: HTTP {e.response.status_code}: {body}") from None
        except httpx.HTTPError as e:
            raise FlickrError(-1, f"{method}: {type(e).__name__}") from None
        except ValueError:
            raise FlickrError(-1, f"{method}: response was not JSON") from None
        if data.get("stat") != "ok":
            raise FlickrError(int(data.get("code", -1)), data.get("message", "unknown error"))
        return data

    # -- users -------------------------------------------------------------

    def user(self, username: str) -> User:
        nsid = self.call("flickr.people.findByUsername", username=username)["user"]["nsid"]
        p = self.call("flickr.people.getInfo", user_id=nsid)["person"]
        return User(
            nsid=nsid,
            username=p.get("username", {}).get("_content", username),
            realname=p.get("realname", {}).get("_content", "") or username,
            profile_url=p.get("profileurl", {}).get("_content", ""),
        )

    # -- groups ------------------------------------------------------------

    def group(self, ref: str) -> Group:
        """Resolve a group NSID ("755579@N24") or URL name ("photographsonthebrain")."""
        if is_group_nsid(ref):
            g = self.call("flickr.groups.getInfo", group_id=ref)["group"]
            return Group(nsid=g["id"], name=g.get("name", {}).get("_content", ref))
        g = self.call("flickr.urls.lookupGroup", url=f"https://www.flickr.com/groups/{ref}/")["group"]
        return Group(nsid=g["id"], name=g.get("groupname", {}).get("_content", ref))

    # -- photo lists -------------------------------------------------------

    def _page(self, block: dict[str, Any], owner: str | None = None, title: str = "") -> PhotoPage:
        return PhotoPage(
            photos=[Photo.from_search(p, owner, self.sizes) for p in block.get("photo", [])],
            page=int(block.get("page", 1)),
            pages=max(1, int(block.get("pages", 1))),
            title=title,
        )

    def search(self, user_id: str, *, machine_tags: str | None = None,
               page: int = 1, per_page: int = 10) -> PhotoPage:
        data = self.call("flickr.photos.search", user_id=user_id, machine_tags=machine_tags,
                         extras=EXTRAS, page=page, per_page=per_page)
        return self._page(data["photos"])

    def photoset(self, set_id: str, *, page: int = 1, per_page: int = 10) -> PhotoPage:
        data = self.call("flickr.photosets.getPhotos", photoset_id=set_id,
                         extras=EXTRAS, page=page, per_page=per_page)
        block = data["photoset"]
        return self._page(block, owner=block.get("owner"), title=block.get("title", ""))

    def group_pool(self, group_id: str, *, page: int = 1, per_page: int = 30) -> PhotoPage:
        data = self.call("flickr.groups.pools.getPhotos", group_id=group_id,
                         extras=EXTRAS, page=page, per_page=per_page)
        return self._page(data["photos"])

    def favorites(self, user_id: str, *, page: int = 1, per_page: int = 30) -> PhotoPage:
        data = self.call("flickr.favorites.getPublicList", user_id=user_id,
                         extras=EXTRAS, page=page, per_page=per_page)
        return self._page(data["photos"])

    # -- single photo ------------------------------------------------------

    def photo(self, photo_id: str) -> Photo:
        info = self.call("flickr.photos.getInfo", photo_id=photo_id)["photo"]
        sizes = self.call("flickr.photos.getSizes", photo_id=photo_id)["sizes"]["size"]
        return Photo.from_info(info, sizes)

