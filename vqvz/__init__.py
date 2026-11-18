"""img.vqvz.com: a photoblog that uses Flickr as its backend."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .cache import CachedFlickr
from .config import from_env, load_sets
from .flickr import FlickrClient


def create_app(overrides: dict[str, Any] | None = None, flickr: Any = None) -> Flask:
    app = Flask(__name__)
    # Behind Caddy/nginx, trust its X-Forwarded-Proto/Host so absolute URLs
    # (link-preview tags) say https://img.vqvz.com, not http://127.0.0.1:8003.
    # Safe as long as the app is only reachable through that one proxy.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # type: ignore[method-assign]
    app.config.update(from_env())
    app.config.update(overrides or {})

    if flickr is None:
        flickr = CachedFlickr(FlickrClient(app.config["FLICKR_API_KEY"]), ttl=app.config["CACHE_TTL"])
    app.extensions["flickr"] = flickr
    app.extensions["sets"] = load_sets(Path(app.config["SETS_FILE"]))

    from .site import bp
    app.register_blueprint(bp)
    return app
