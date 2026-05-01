from markr.api.errors import MarkrHTTPException


def test_carries_fields() -> None:
    e = MarkrHTTPException(422, "wrong_root", "msg", {"got": "x"})

    assert e.status_code == 422
    assert e.error == "wrong_root"
    assert e.message == "msg"
    assert e.details == {"got": "x"}


def test_default_details() -> None:
    e = MarkrHTTPException(400, "malformed_xml", "bad")

    assert e.details == {}
