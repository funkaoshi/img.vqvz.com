"""img.vqvz.com: a photoblog that uses Flickr as its backend."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Flask

from .cache import CachedFlickr
from .config import from_env, load_sets
from .flickr import FlickrClient


def create_app(overrides: dict[str, Any] | None = None, flickr: Any = None) -> Flask:
    app = Flask(__name__)
    app.config.update(from_env())
    app.config.update(overrides or {})

    if flickr is None:
        flickr = CachedFlickr(FlickrClient(app.config["FLICKR_API_KEY"]), ttl=app.config["CACHE_TTL"])
    app.extensions["flickr"] = flickr
    app.extensions["sets"] = load_sets(Path(app.config["SETS_FILE"]))

    from .site import bp
    app.register_blueprint(bp)
    return app
