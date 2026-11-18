"""img.vqvz.com and gv.vqvz.com: two small sites that use Flickr as a backend.

One package and one image; VQVZ_SITE (img or gv) chooses which site runs.
"""

from __future__ import annotations

import os
from importlib import import_module
from typing import Any

from flask import Flask
from jinja2 import ChoiceLoader, FileSystemLoader
from werkzeug.middleware.proxy_fix import ProxyFix

from . import web
from .cache import CachedFlickr
from .config import from_env
from .flickr import FlickrClient


def create_app(overrides: dict[str, Any] | None = None, flickr: Any = None,
               site: str | None = None) -> Flask:
    site = site or os.environ.get("VQVZ_SITE", "img")
    module = import_module(f".{site}", __name__)  # vqvz.img or vqvz.gv

    app = Flask(__name__, template_folder=f"templates/{site}")
    # Each site's own templates first, then ones both sites share.
    app.jinja_loader = ChoiceLoader([
        FileSystemLoader(f"{app.root_path}/templates/{site}"),
        FileSystemLoader(f"{app.root_path}/templates/shared"),
    ])
    # Behind Caddy/nginx, trust its X-Forwarded-Proto/Host so absolute URLs
    # (link-preview tags) say https://img.vqvz.com, not http://127.0.0.1:8003.
    # Safe as long as the app is only reachable through that one proxy.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # type: ignore[method-assign]
    app.config.update(from_env(site))
    app.config.update(overrides or {})

    if flickr is None:
        client = FlickrClient(app.config["FLICKR_API_KEY"], sizes=module.IMAGE_SIZES)
        flickr = CachedFlickr(client, ttl=app.config["CACHE_TTL"])
    app.extensions["flickr"] = flickr

    web.install(app)
    module.init_app(app)
    return app
