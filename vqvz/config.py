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


def from_env(env: os._Environ[str] | dict[str, str] = os.environ) -> dict[str, object]:
    return {
        "FLICKR_API_KEY": env.get("FLICKR_API_KEY", ""),
        "FLICKR_USERNAME": env.get("FLICKR_USERNAME", "funkaoshi"),
        "SITE_TITLE": env.get("SITE_TITLE", "IMG VQVZ"),
        "SITE_DESCRIPTION": env.get("SITE_DESCRIPTION", "Photographs by Ramanan Sivaranjan."),
        "SITE_OWNER": env.get("SITE_OWNER", "Ramanan Sivaranjan"),
        "SITE_SINCE": int(env.get("SITE_SINCE", "2009")),
        "ANALYTICS_ID": env.get("ANALYTICS_ID", ""),
        "PER_PAGE": int(env.get("PER_PAGE", "10")),
        "CACHE_TTL": int(env.get("CACHE_TTL", "300")),
        "SETS_FILE": env.get("SETS_FILE", str(ROOT / "sets.yml")),
    }
