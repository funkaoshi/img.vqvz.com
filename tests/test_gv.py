import re

import pytest

from conftest import meta
from vqvz.gv import parse_group


def hrefs(html, cls):
    return set(re.findall(rf'class="{cls}" rel="\w+" href="([^"]+)"', html))


def test_index_has_form_and_featured_groups(gv_client):
    html = gv_client.get("/").get_data(as_text=True)
    assert "Flickr Group Viewer" in html
    assert 'action="/group"' in html
    assert 'href="/group/755579@N24">Photographs on the Brain</a>' in html


def test_group_by_nsid(gv_client, fake):
    r = gv_client.get("/group/755579@N24")
    html = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "Viewing Photographs on the Brain" in html
    assert html.count('class="photo hentry"') == 30
    assert any(c["method"] == "flickr.groups.pools.getPhotos" and c.get("per_page") == "30"
               for c in fake.calls)


def test_group_by_url_name(gv_client, fake):
    # The old gv README's TODO: /group/<url name> as well as /group/<nsid>.
    html = gv_client.get("/group/photographsonthebrain").get_data(as_text=True)
    assert "Viewing Photographs on the Brain" in html
    assert any(c["method"] == "flickr.urls.lookupGroup" for c in fake.calls)


def test_group_paging_uses_pg_param(gv_client):
    html = gv_client.get("/group/755579@N24").get_data(as_text=True)
    assert "1 of 2" in html
    assert hrefs(html, "next_page") == {"/group/755579@N24?pg=2"}
    html = gv_client.get("/group/755579@N24?pg=2").get_data(as_text=True)
    assert hrefs(html, "prev_page") == {"/group/755579@N24"}
    assert 'class="next_page"' not in html
    assert gv_client.get("/group/755579@N24?pg=3").status_code == 404


def test_group_shows_640px_images_and_photographer(gv_client):
    html = gv_client.get("/group/755579@N24").get_data(as_text=True)
    assert "_abc_z.jpg" in html and "_abc_b.jpg" not in html
    assert 'by <a href="https://www.flickr.com/photos/funkaoshi/">funkaoshi</a>' in html


def test_unknown_group_is_404(gv_client):
    r = gv_client.get("/group/0@N00")
    assert r.status_code == 404 and "WTF?!" in r.get_data(as_text=True)
    assert gv_client.get("/group/nosuchgroup").status_code == 404


def test_favourites(gv_client):
    html = gv_client.get("/favs/funkaoshi").get_data(as_text=True)
    assert "Viewing funkaoshi&#39;s Favourites" in html  # apostrophe is escaped
    assert html.count('class="photo hentry"') == 30


@pytest.mark.parametrize("typed,ref", [
    ("https://www.flickr.com/groups/onthestreet/", "onthestreet"),
    ("http://flickr.com/groups/onthestreet", "onthestreet"),
    ("flickr.com/groups/755579@N24/pool/", "755579@N24"),
    ("  photographsonthebrain ", "photographsonthebrain"),
    ("755579@N24", "755579@N24"),
    ("https://example.com/nope", None),
    ("two words", None),
])
def test_parse_group(typed, ref):
    assert parse_group(typed) == ref


def test_form_redirects_to_group(gv_client):
    for method in (gv_client.get, gv_client.post):
        r = method("/group", query_string={"url": "https://www.flickr.com/groups/photographsonthebrain/"})
        assert r.status_code == 303 and r.headers["Location"] == "/group/photographsonthebrain"


def test_form_with_junk_explains(gv_client):
    r = gv_client.get("/group", query_string={"url": "https://example.com/nope"})
    assert r.status_code == 400 and "doesn't look like a Flickr group URL" in r.get_data(as_text=True)


def test_empty_form_goes_home(gv_client):
    r = gv_client.get("/group")
    assert r.status_code == 302 and r.headers["Location"] == "/"


def test_img_routes_not_on_gv(gv_client):
    assert gv_client.get("/sets").status_code == 404
    assert gv_client.get("/about").status_code == 404


def test_form_is_prefilled_on_every_page(gv_client):
    # Regression: macros imported without context rendered value="".
    for path in ("/", "/group/755579@N24", "/group/0@N00"):
        html = gv_client.get(path).get_data(as_text=True)
        assert 'value="https://www.flickr.com/groups/onthestreet/"' in html, path


def test_gv_link_preview(gv_client):
    html = gv_client.get("/group/755579@N24").get_data(as_text=True)
    assert meta(html, "og:title") == "Viewing Photographs on the Brain"
    assert meta(html, "og:image").endswith("_abc_z.jpg")
    html = gv_client.get("/").get_data(as_text=True)
    assert meta(html, "og:title") == "Flickr Group Viewer" and meta(html, "twitter:card") == "summary"
