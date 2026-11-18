"""Settings come from the environment; curated sets come from sets.yml."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class CuratedSet:
    slug: str
    set_id: str
    title: str
    thumbnail: str


def load_sets(path: Path) -> dict[str, CuratedSet]:
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text()) or {}
    return {
        slug: CuratedSet(slug=slug, set_id=str(s["set_id"]), title=s["title"], thumbnail=s["thumbnail"])
        for slug, s in raw.items()
    }


SITES = ("img", "gv")

# Per-site defaults; any of them can be overridden by an environment variable
# of the same name.
DEFAULTS: dict[str, dict[str, object]] = {
    "img": {
        "SITE_TITLE": "IMG VQVZ",
        "SITE_DESCRIPTION": "Photographs by Ramanan Sivaranjan.",
        "SITE_SINCE": 2009,
        "PER_PAGE": 10,
    },
    "gv": {
        "SITE_TITLE": "GROUP VIEWQVZ",
        "SITE_DESCRIPTION": "Flickr Group Viewer",
        "SITE_SINCE": 2010,
        "PER_PAGE": 30,
        # Pre-filled in the "view a group" form.
        "DEFAULT_GROUP_URL": "https://www.flickr.com/groups/onthestreet/",
    },
}

COMMON: dict[str, object] = {
    "FLICKR_API_KEY": "",
    "FLICKR_USERNAME": "funkaoshi",
    "SITE_OWNER": "Ramanan Sivaranjan",
    "ANALYTICS_ID": "",
    "CACHE_TTL": 300,
    "SETS_FILE": str(ROOT / "sets.yml"),
}


def from_env(site: str, env: os._Environ[str] | dict[str, str] = os.environ) -> dict[str, object]:
    """Settings for `site`: its defaults, overridden by matching env vars.

    Values are coerced to the default's type, so PER_PAGE=20 becomes an int.
    """
    if site not in SITES:
        raise ValueError(f"unknown site {site!r}; expected one of {SITES}")
    settings = {**COMMON, **DEFAULTS[site]}
    for key, default in settings.items():
        if key in env:
            settings[key] = type(default)(env[key])
    settings["SITE"] = site
    return settings
