# img.vqvz.com

A Claude rewrite of [the original img.vqvz.com Sinatra web application][0], rewritten 
in Flask. A photoblog that uses Flickr as its backend: a paged photostream, curated 
sets, machine-tag sets (`vqvz:set=<name>`), single-photo pages, and j/k keyboard
paging.

## Run

    # save FLICKR_API_KEY=... in .env file. 
    # Get key from https://www.flickr.com/services/apps/create
    uv sync --extra dev
    uv run flask --app vqvz run --debug

    # tests
    uv run pytest

## Settings (environment variables)

| Variable | Default |
|---|---|
| `FLICKR_API_KEY` | (required) |
| `FLICKR_USERNAME` | `USERNAME` |
| `SITE_TITLE` / `SITE_DESCRIPTION` / `SITE_OWNER` / `SITE_SINCE` | IMG VQVZ / ... |
| `ANALYTICS_ID` | empty, so no analytics |
| `PER_PAGE` | `10` |
| `CACHE_TTL` | `300` seconds (in-process cache and `Cache-Control`) |
| `SETS_FILE` | `./sets.yml` |

## URLs

| URL | Shows |
|---|---|
| `/`, `/page/N` | photostream |
| `/sets` | curated sets from `sets.yml` |
| `/set/<flickr set id>?page=N` | any Flickr set |
| `/set/<slug>?page=N` | curated set, else photos tagged `vqvz:set=<slug>` |
| `/photo/<id>` | one photo |
| `/about`, `/news` | `vqvz/templates/pages/*.html` |

## Layout

- `vqvz/flickr.py`: site-agnostic client and models (`Photo`, `Listing`). Has
  `group_pool` / `favorites` so gv.vqvz.com can be added as another blueprint.
- `vqvz/cache.py`: a TTL cache in front of the client.
- `vqvz/site.py`: routes, error handling, cache headers.

[0]: https://funkaoshi.com/blog/img-vqvz

## Behind a reverse proxy

Pages carry link-preview tags (Open Graph and `twitter:card`), so a shared link shows
the first photo on the page as its thumbnail on Bluesky, X, Mastodon, etc. Those tags
need the public URL, so the app trusts the proxy's `X-Forwarded-Proto` and
`X-Forwarded-Host` headers. Caddy sends these by default; with nginx add
`proxy_set_header X-Forwarded-Proto $scheme;` and `proxy_set_header X-Forwarded-Host $host;`.
Only publish the app's port on `127.0.0.1`, so nothing can bypass the proxy.
