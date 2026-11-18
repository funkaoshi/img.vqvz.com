import re

from conftest import meta


def nav_hrefs(html, cls):
    return set(re.findall(rf'href="([^"]+)" class="{cls}"', html))


def test_home_is_page_one_of_stream(client, fake):
    r = client.get("/")
    html = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "Page 1 of 3" in html
    assert html.count('class="photo hentry"') == 10
    assert nav_hrefs(html, "next_page") == {"/page/2"}
    assert 'class="prev_page"' not in html


def test_middle_page_links_both_ways(client):
    html = client.get("/page/2").get_data(as_text=True)
    assert nav_hrefs(html, "prev_page") == {"/"}
    assert nav_hrefs(html, "next_page") == {"/page/3"}


def test_last_page_has_no_next(client):
    html = client.get("/page/3").get_data(as_text=True)
    assert nav_hrefs(html, "prev_page") == {"/page/2"}
    assert 'class="next_page"' not in html


def test_page_one_redirects_home(client):
    r = client.get("/page/1")
    assert r.status_code == 301 and r.headers["Location"] == "/"


def test_past_the_end_is_404(client):
    assert client.get("/page/4").status_code == 404
    assert client.get("/page/0").status_code == 404


def test_photo_titles_are_shown_not_untitled(client):
    # The Ruby version checked @tile instead of @title, so everything was "untitled".
    html = client.get("/").get_data(as_text=True)
    assert ">Photo 0</a>" in html and "untitled" not in html


def test_sets_page_lists_curated_sets(client):
    html = client.get("/sets").get_data(as_text=True)
    assert "<h2>Sets</h2>" in html
    assert 'href="/set/blansdowne"' in html and "Stray Dogs" in html


def test_set_by_id_is_paginated(client, fake):
    html = client.get("/set/72157608508468675").get_data(as_text=True)
    assert "Set 72157608508468675" in html
    assert nav_hrefs(html, "next_page") == {"/set/72157608508468675?page=2"}
    html = client.get("/set/72157608508468675?page=2").get_data(as_text=True)
    assert nav_hrefs(html, "prev_page") == {"/set/72157608508468675"}


def test_curated_set_uses_photoset_id_from_sets_yml(client, fake):
    html = client.get("/set/blansdowne").get_data(as_text=True)
    assert "<h2>Blansdowne</h2>" in html
    assert any(c.get("photoset_id") == "72157619603386788" for c in fake.calls)


def test_unknown_slug_falls_back_to_machine_tag(client, fake):
    r = client.get("/set/shima")
    assert r.status_code == 200
    assert any(c.get("machine_tags") == "vqvz:set=shima" for c in fake.calls)
    assert r.get_data(as_text=True).count('class="photo hentry"') == 2


def test_unknown_slug_with_no_tagged_photos_is_404(client):
    assert client.get("/set/nothing-here").status_code == 404


def test_single_photo(client):
    html = client.get("/photo/4196874052").get_data(as_text=True)
    assert "<h2>Shima</h2>" in html
    assert 'src="https://live.staticflickr.com/1/x_b.jpg"' in html


def test_flickr_titles_are_escaped(client, fake):
    fake.photo_title = "<script>alert(1)</script>"
    html = client.get("/photo/1").get_data(as_text=True)
    assert "<script>alert(1)" not in html and "&lt;script&gt;" in html


def test_static_pages_render(client):
    # The Ruby /:name route never set @name, so these always errored.
    assert "<h2>About</h2>" in client.get("/about").get_data(as_text=True)
    assert "<h2>News</h2>" in client.get("/news").get_data(as_text=True)


def test_unknown_static_page_is_404_wtf(client):
    r = client.get("/nope")
    assert r.status_code == 404 and "<h2>WTF</h2>" in r.get_data(as_text=True)


def test_flickr_not_found_maps_to_404(client, fake):
    fake.fail_with = (1, "Photo not found")
    assert client.get("/photo/999").status_code == 404


def test_flickr_outage_maps_to_502(client, fake):
    fake.fail_with = (105, "Service currently unavailable")
    r = client.get("/")
    assert r.status_code == 502 and "Flickr isn't answering" in r.get_data(as_text=True)


def test_app_boots_without_network(fake):
    # Old app called Flickr at boot; a Flickr outage meant the site couldn't start.
    from vqvz import create_app
    create_app({"TESTING": True})
    assert fake.calls == []


def test_cache_headers_only_on_success(client):
    assert client.get("/").headers["Cache-Control"] in ("public, max-age=300", "max-age=300, public")
    assert "max-age" not in client.get("/nope").headers.get("Cache-Control", "")


def test_flickr_responses_are_cached(client, fake):
    client.get("/page/2")
    n = len(fake.calls)
    client.get("/page/2")
    assert len(fake.calls) == n


def test_analytics_only_when_configured(fake):
    from vqvz import create_app
    html = create_app({"TESTING": True, "ANALYTICS_ID": ""}).test_client().get("/about").get_data(as_text=True)
    assert "googletagmanager" not in html
    html = create_app({"TESTING": True, "ANALYTICS_ID": "G-TEST"}).test_client().get("/about").get_data(as_text=True)
    assert '"G-TEST"' in html



def test_link_preview_uses_first_photo(client):
    html = client.get("/page/2").get_data(as_text=True)
    first = re.search(r'<img src="([^"]+)"', html.split('id="content"')[1]).group(1)
    assert meta(html, "og:image") == first
    assert meta(html, "twitter:card") == "summary_large_image"
    assert meta(html, "og:title") == "IMG VQVZ"
    assert meta(html, "og:image:alt") == "Photo 10"


def test_link_preview_on_photo_and_set_pages(client):
    html = client.get("/photo/4196874052").get_data(as_text=True)
    assert meta(html, "og:image") == "https://live.staticflickr.com/1/x_b.jpg"
    assert meta(html, "og:title") == "Shima :: IMG VQVZ"
    html = client.get("/set/blansdowne").get_data(as_text=True)
    assert meta(html, "og:title") == "IMG VQVZ :: Blansdowne"
    assert meta(html, "og:image").endswith("_abc_b.jpg")


def test_pages_without_photos_get_text_card(client):
    html = client.get("/about").get_data(as_text=True)
    assert meta(html, "twitter:card") == "summary" and meta(html, "og:image") is None
    assert meta(html, "og:title") == "IMG VQVZ :: About"


def test_link_preview_url_is_https_behind_proxy(client):
    # Caddy/nginx talk to the app over http on localhost; ProxyFix restores the public URL.
    html = client.get("/page/2", headers={"X-Forwarded-Proto": "https",
                                          "X-Forwarded-Host": "img.vqvz.com"}).get_data(as_text=True)
    assert meta(html, "og:url") == "https://img.vqvz.com/page/2"


def test_link_preview_escapes_titles(client, fake):
    fake.photo_title = 'Say "cheese" <b>'
    html = client.get("/photo/1").get_data(as_text=True)
    assert meta(html, "og:image:alt") == "Say &#34;cheese&#34; &lt;b&gt;"
