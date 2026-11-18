"""Web plumbing shared by both sites: Flickr access, listings, errors, caching."""

from __future__ import annotations

from datetime import date
from typing import Callable

from flask import Flask, abort, current_app, render_template, request
from werkzeug.exceptions import HTTPException

from .flickr import FlickrError, Listing, PhotoPage


def flickr():
    return current_app.extensions["flickr"]


def per_page() -> int:
    return current_app.config["PER_PAGE"]


def page_arg(name: str = "page") -> int:
    page = request.args.get(name, 1, type=int)
    if page < 1:
        abort(404)
    return page


def make_listing(title: str, result: PhotoPage, url_for_page: Callable[[int], str]) -> Listing:
    if result.page > result.pages:  # Flickr happily returns nothing past the end
        abort(404)
    return Listing(title=title, photos=result.photos, page=result.page,
                   pages=result.pages, url_for_page=url_for_page)


def render_error(status: int):
    """Each site's templates provide their own error.html."""
    return render_template("error.html", status=status), status


def install(app: Flask) -> None:
    @app.context_processor
    def site_globals():
        cfg = app.config
        return {
            "site_title": cfg["SITE_TITLE"],
            "site_owner": cfg["SITE_OWNER"],
            "site_since": cfg["SITE_SINCE"],
            "analytics_id": cfg["ANALYTICS_ID"],
            "this_year": date.today().year,
        }

    @app.errorhandler(FlickrError)
    def flickr_error(e: FlickrError):
        app.logger.warning("%s", e)
        return render_error(404 if e.not_found else 502)

    @app.errorhandler(HTTPException)
    def http_error(e: HTTPException):
        if e.code and e.code >= 400:
            return render_error(e.code)
        return e

    @app.errorhandler(Exception)
    def server_error(e: Exception):
        app.logger.exception("unhandled error")
        return render_error(500)

    @app.after_request
    def cache_headers(resp):
        # Let browsers and any proxy/CDN hold successful pages for CACHE_TTL.
        # (The Ruby sites' Rack::Cache never stored anything: nothing sent this.)
        if request.method == "GET" and resp.status_code == 200:
            resp.cache_control.public = True
            resp.cache_control.max_age = app.config["CACHE_TTL"]
        return resp
