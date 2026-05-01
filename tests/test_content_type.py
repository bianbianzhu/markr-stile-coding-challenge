import pytest

from markr.api.content_type import require_markr_xml
from markr.api.errors import MarkrHTTPException


@pytest.mark.parametrize(
    "content_type",
    [
        "text/xml+markr",
        "text/xml+markr; charset=utf-8",
        " TEXT/XML+MARKR ; charset=utf-8 ",
    ],
)
def test_accepted(content_type):
    require_markr_xml(content_type)


@pytest.mark.parametrize(
    "content_type",
    [
        None,
        "",
        "   ",
        "text/xml",
        "application/xml",
        "text/xml+markr-bad",
        "application/json",
    ],
)
def test_rejected(content_type):
    with pytest.raises(MarkrHTTPException) as exc_info:
        require_markr_xml(content_type)

    assert exc_info.value.status_code == 415
    assert exc_info.value.error == "unsupported_media_type"
    assert exc_info.value.details == {"got": (content_type or "").split(";", 1)[0].strip().lower()}
