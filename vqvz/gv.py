"""gv.vqvz.com: browse a Flickr group pool (or someone's favourites) with j/k.

URLs are the same as the 2010 Sinatra version, so old links keep working:

    /                       pick a group
    /group/<group>?pg=N     a group pool; <group> is an NSID or the URL name
    /favs/<username>?pg=N   someone's public favourites
    /group?url=<flickr url> form target; redirects to /group/<group>
"""

from __future__ import annotations

import re

from flask import Blueprint, Flask, abort, current_app, redirect, render_template, request, url_for

from .flickr import MEDIUM_640
from .web import flickr, make_listing, page_arg, per_page

IMAGE_SIZES = MEDIUM_640

bp = Blueprint("gv", __name__)

# From the original front page: "group pools I think are pretty damn good".
FEATURED_GROUPS = [
    ("Contract Killers", "474579@N20"),
    ("Hardcore Street Photography", "94761711@N00"),
    ("La Familia Abrazada", "868185@N20"),
    ("La Pura Vida", "760034@N25"),
    ("Photographs on the Brain", "755579@N24"),
    ("Your Photo Isn't Really That Great", "1048863@N23"),
]

# A group is named by its NSID (755579@N24) or its URL name (photographsonthebrain).
GROUP_REF = re.compile(r"^[\w.@-]+$")
GROUP_URL = re.compile(r"^(?:https?://)?(?:www\.)?flickr\.com/groups/([\w.@-]+)", re.IGNORECASE)
USERNAME = re.compile(r"^[^/\s][^/]{0,63}$")


def init_app(app: Flask) -> None:
    app.register_blueprint(bp)

    @app.context_processor
    def gv_globals():
        return {"default_group_url": current_app.config["DEFAULT_GROUP_URL"]}


def parse_group(text: str) -> str | None:
    """Turn what someone typed into the form into a group reference."""
    text = text.strip()
    m = GROUP_URL.match(text)
    if m:
        return m.group(1)
    return text if GROUP_REF.match(text) else None


@bp.get("/")
def index():
    return render_template("index.html", featured=FEATURED_GROUPS)


@bp.get("/group/")
@bp.route("/group", methods=["GET", "POST"])  # registered first, so url_for gives /group
def find_group():
    text = request.values.get("url", "")
    if not text:
        return redirect(url_for(".index"))
    ref = parse_group(text)
    if ref is None:
        return render_template("index.html", featured=FEATURED_GROUPS, error=text), 400
    return redirect(url_for(".group", ref=ref), 303)


@bp.get("/group/<ref>")
def group(ref: str):
    if not GROUP_REF.match(ref):
        abort(404)
    page = page_arg("pg")
    g = flickr().group(ref)
    result = flickr().group_pool(g.nsid, page=page, per_page=per_page())
    return render_template("listing.html", listing=make_listing(
        g.name, result, lambda n: url_for(".group", ref=ref, pg=n if n > 1 else None)))


@bp.get("/favs/<username>")
def favs(username: str):
    if not USERNAME.match(username):
        abort(404)
    page = page_arg("pg")
    user = flickr().user(username)
    result = flickr().favorites(user.nsid, page=page, per_page=per_page())
    return render_template("listing.html", listing=make_listing(
        f"{user.username}'s Favourites", result,
        lambda n: url_for(".favs", username=username, pg=n if n > 1 else None)))
