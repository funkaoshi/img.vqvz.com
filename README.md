# img.vqvz.com and gv.vqvz.com

A Claude rewrite of [the original img.vqvz.com Sinatra web application][0], rewritten
in Flask, together with its sister site [gv.vqvz.com][1]. Both use Flickr as their
backend:

- **img.vqvz.com** is a photoblog: a paged photostream, curated sets, machine-tag
  sets (`vqvz:set=<name>`), single-photo pages, and j/k keyboard paging.
- **gv.vqvz.com** (Flickr Group Viewer) browses a Flickr group pool, or someone's
  public favourites, with the same j/k paging.

One package and one Docker image; `VQVZ_SITE` (`img` or `gv`) picks the site.

## Run

    # save FLICKR_API_KEY=... in .env file.
    # Get key from https://www.flickr.com/services/apps/create
    uv sync --extra dev
    uv run flask --app vqvz run --debug                 # img
    VQVZ_SITE=gv uv run flask --app vqvz run --debug    # gv

    # tests
    uv run pytest

## Docker

    docker buildx build --platform linux/amd64,linux/arm64 -t funkaoshi/img-vqvz:latest --push .

    # img.vqvz.com and gv.vqvz.com from the same image
    docker run -d --name img-vqvz --restart unless-stopped -p 127.0.0.1:8003:8003 \
      --env-file /etc/vqvz.env funkaoshi/img-vqvz:latest
    docker run -d --name gv-vqvz --restart unless-stopped -p 127.0.0.1:8004:8003 \
      --env-file /etc/vqvz.env -e VQVZ_SITE=gv funkaoshi/img-vqvz:latest

Put a reverse proxy in front for HTTPS, e.g. with Caddy:

    img.vqvz.com { reverse_proxy 127.0.0.1:8003 }
    gv.vqvz.com  { reverse_proxy 127.0.0.1:8004 }

The app trusts the proxy's `X-Forwarded-Proto` and `X-Forwarded-Host` headers, so
link-preview tags (`og:url`, used by Bluesky, X, etc.) get the public `https://` URL.
Caddy sends these by default; with nginx add
`proxy_set_header X-Forwarded-Proto $scheme;` and `proxy_set_header X-Forwarded-Host $host;`.
Only publish the container's port on `127.0.0.1`, so nothing can bypass the proxy.

## Settings (environment variables)

| Variable | Default |
|---|---|
| `VQVZ_SITE` | `img` (or `gv`) |
| `FLICKR_API_KEY` | (required) |
| `FLICKR_USERNAME` | `USERNAME` (img: whose photostream to show) |
| `SITE_TITLE` / `SITE_DESCRIPTION` / `SITE_OWNER` / `SITE_SINCE` | per site: IMG VQVZ / GROUP VIEWQVZ / ... |
| `ANALYTICS_ID` | empty, so no analytics |
| `PER_PAGE` | img `10`, gv `30` |
| `CACHE_TTL` | `300` seconds (in-process cache and `Cache-Control`) |
| `SETS_FILE` | `./sets.yml` (img) |
| `DEFAULT_GROUP_URL` | gv: pre-filled in the group form |

## URLs

img.vqvz.com:

| URL | Shows |
|---|---|
| `/`, `/page/N` | photostream |
| `/sets` | curated sets from `sets.yml` |
| `/set/<flickr set id>?page=N` | any Flickr set |
| `/set/<slug>?page=N` | curated set, else photos tagged `vqvz:set=<slug>` |
| `/photo/<id>` | one photo |
| `/about`, `/news` | `vqvz/templates/img/pages/*.html` |

gv.vqvz.com (same URLs as the 2010 version):

| URL | Shows |
|---|---|
| `/` | pick a group |
| `/group/<group>?pg=N` | a group pool; `<group>` is an NSID (`755579@N24`) or URL name (`photographsonthebrain`) |
| `/favs/<username>?pg=N` | someone's public favourites |
| `/group?url=<flickr group url>` | form target; redirects to `/group/<group>` |

## Layout

- `vqvz/flickr.py`: site-agnostic client and models (`Photo`, `Listing`, `Group`).
- `vqvz/cache.py`: a TTL cache in front of the client.
- `vqvz/web.py`: shared plumbing: listings, error handling, cache headers.
- `vqvz/img.py`, `vqvz/gv.py`: each site's routes.
- `vqvz/templates/img/`, `vqvz/templates/gv/`: each site's templates.
  `vqvz/static/` holds both stylesheets and the shared j/k script.

[0]: https://funkaoshi.com/blog/img-vqvz
[1]: https://github.com/funkaoshi/gv.vqvz.com
