from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_cart_is_hidden_in_initial_markup_and_inert():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    button = re.search(r'<button class="cart-button" id="open-cart"([^>]*)>', html)
    overlay = re.search(r'<div class="overlay" id="cart-overlay"([^>]*)>', html)
    assert button and 'aria-expanded="false"' in button.group(1)
    assert 'aria-controls="cart-overlay"' in button.group(1)
    assert overlay and re.search(r"\bhidden\b", overlay.group(1))
    assert re.search(r"\baria-hidden=\"true\"", overlay.group(1))
    assert re.search(r"\binert(?:\s|$)", overlay.group(1))
    assert '<aside class="cart-drawer" role="dialog" aria-modal="true" aria-labelledby="cart-title">' in html


def test_hidden_cart_cannot_be_overridden_by_overlay_display_style():
    css = (ROOT / "styles.css").read_text(encoding="utf-8")
    compact = re.sub(r"\s+", "", css)
    assert ".overlay[hidden]" in compact
    assert re.search(r"(?:\.overlay|#cart-overlay)\[hidden\]\{[^}]*display:none!important", compact)


def test_cart_open_close_keeps_visibility_and_accessibility_state_in_sync():
    js = (ROOT / "app.js").read_text(encoding="utf-8")
    assert 'overlay.hidden=false;' in js
    assert 'overlay.inert=false;' in js
    assert 'overlay.setAttribute("aria-hidden","false")' in js
    assert 'overlay.hidden=true;' in js
    assert 'overlay.inert=true;' in js
    assert 'overlay.setAttribute("aria-hidden","true")' in js
    assert '$("open-cart").setAttribute("aria-expanded","true")' in js
    assert '$("open-cart").setAttribute("aria-expanded","false")' in js
    assert 'closeCart(false);' in js
