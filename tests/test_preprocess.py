from onenote_archive.preprocess import parse_multipart, sanitize_title, strip_multipart


def test_strip_multipart_keeps_html():
    raw = "--abc\nContent-Type: text/html\n\n<html><body>hi</body></html>\n--abc--"
    out = strip_multipart(raw)
    assert out.strip().startswith("<html")
    assert "hi" in out


def test_parse_multipart_extracts_inkml_sibling():
    raw = (
        "--bound\nContent-Type: text/html\n\n"
        "<html><body>hi</body></html>\n"
        "--bound\nContent-Type: application/inkml+xml\n\n"
        '<inkml:ink xmlns:inkml="http://www.w3.org/2003/InkML"></inkml:ink>\n'
        "--bound--"
    )
    html, ink = parse_multipart(raw)
    assert "hi" in html
    assert ink is not None
    assert "inkml:ink" in ink


def test_sanitize_title():
    assert sanitize_title("20180830: Glycolysis / PPP?") == "20180830-Glycolysis-PPP"
