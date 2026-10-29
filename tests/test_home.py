from django.template.loader import render_to_string


def test_homepage_returns_ok(client):
    response = client.get("/")

    assert response.status_code == 200
    content = response.content.decode()
    assert "Main navigation" in content
    assert "css/app.css" in content
    assert "js/vendor/htmx.min.js" in content
    assert "js/vendor/alpine.min.js" in content
    assert 'hx-get="/demo/swap/"' in content
    assert 'x-data="{ swaps: 0 }"' in content


def test_demo_swap_returns_partial(client):
    response = client.get("/demo/swap/")

    assert response.status_code == 200
    content = response.content.decode()
    assert "HTMX replaced this content" in content
    assert "<html" not in content


def test_base_layout_renders_messages():
    content = render_to_string("base.html", {"messages": ["Changes saved"]})

    assert 'aria-label="Messages"' in content
    assert 'role="status"' in content
    assert "Changes saved" in content
