"""img.vqvz.com: one person's Flickr photostream as a photoblog."""

from __future__ import annotations

import re
from pathlib import Path

from flask import Blueprint, Flask, abort, current_app, redirect, render_template, request, url_for

from .config import load_sets
from .flickr import LARGE_FIRST
from .web import flickr, make_listing, page_arg, per_page

IMAGE_SIZES = LARGE_FIRST

bp = Blueprint("img", __name__)

PAGES_DIR = Path(__file__).parent / "templates" / "img" / "pages"
# Static pages are an allow-list fixed at import time: no filesystem probing per request.
STATIC_PAGES = frozenset(p.stem for p in PAGES_DIR.glob("*.html"))
SLUG = re.compile(r"^[a-z0-9_-]+$")


def init_app(app: Flask) -> None:
    app.extensions["sets"] = load_sets(Path(app.config["SETS_FILE"]))
    app.register_blueprint(bp)


def curated_sets():
    return current_app.extensions["sets"]


def user_nsid() -> str:
    return flickr().user(current_app.config["FLICKR_USERNAME"]).nsid


# -- photostream -------------------------------------------------------------

@bp.get("/")
@bp.get("/page/<int:page>")
def stream(page: int = 1):
    if page == 1 and request.path != "/":
        return redirect(url_for(".stream"), 301)
    if page < 1:
        abort(404)
    result = flickr().search(user_nsid(), page=page, per_page=per_page())
    listing = make_listing(current_app.config["SITE_DESCRIPTION"], result,
                           lambda n: url_for(".stream", page=n) if n > 1 else url_for(".stream"))
    return render_template("listing.html", listing=listing)


# -- sets ----------------------------------------------------------------------

@bp.get("/sets")
def sets():
    return render_template("sets.html", sets=curated_sets().values())


@bp.get("/set/<int:set_id>")
def photoset(set_id: int):
    page = page_arg()
    result = flickr().photoset(str(set_id), page=page, per_page=per_page())
    return render_template("listing.html", listing=make_listing(
        result.title or f"Set {set_id}", result,
        lambda n: url_for(".photoset", set_id=set_id, page=n if n > 1 else None)))


@bp.get("/set/<slug>")
def named_set(slug: str):
    """A curated set from sets.yml, or else photos machine-tagged vqvz:set=<slug>."""
    if not SLUG.match(slug):
        abort(404)
    page = page_arg()
    url = lambda n: url_for(".named_set", slug=slug, page=n if n > 1 else None)  # noqa: E731
    curated = curated_sets().get(slug)
    if curated:
        result = flickr().photoset(curated.set_id, page=page, per_page=per_page())
        title = curated.title
    else:
        result = flickr().search(user_nsid(), machine_tags=f"vqvz:set={slug}",
                                 page=page, per_page=per_page())
        if not result.photos:
            abort(404)
        title = slug.replace("-", " ").replace("_", " ").title()
    return render_template("listing.html", listing=make_listing(title, result, url))


# -- single photo ----------------------------------------------------------------

@bp.get("/photo/<int:photo_id>")
def photo(photo_id: int):
    return render_template("photo.html", photo=flickr().photo(str(photo_id)))


# -- static pages ----------------------------------------------------------------

@bp.get("/<name>")
def static_page(name: str):
    if name not in STATIC_PAGES:
        abort(404)
    return render_template("page.html", name=name, content=f"pages/{name}.html")
