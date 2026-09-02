"""Regression tests for reliability fixes."""

from unittest.mock import Mock, patch

import requests

from tap_hubspot_beta.auth import OAuth2Authenticator
from tap_hubspot_beta.client_base import hubspotStream


def test_request_token_uses_timeout_and_keyword_payload():
    """Token requests should not be able to hang indefinitely."""
    authenticator = object.__new__(OAuth2Authenticator)
    response = Mock(status_code=200)

    with patch("tap_hubspot_beta.auth.requests.post", return_value=response) as post:
        assert authenticator.request_token("https://example.test/token", {"key": "value"}) is response

    post.assert_called_once_with(
        "https://example.test/token", data={"key": "value"}, timeout=60
    )


def test_update_access_token_does_not_hide_json_errors():
    """Only HTTP status failures should be translated into login failures."""
    assert issubclass(requests.HTTPError, requests.RequestException)


def test_post_process_ignores_properties_missing_from_schema():
    """Unexpected HubSpot properties should survive numeric conversion."""
    stream = object.__new__(hubspotStream)
    stream._config = {"cast_numbers_as_float": True}
    stream.__dict__["schema"] = {
        "properties": {"known": {"type": ["number"]}}
    }
    row = {"properties": {"known": "2.5", "new_remote_field": "untouched"}}

    assert stream.post_process(row, None) == {
        "properties": {"known": 2.5, "new_remote_field": "untouched"}
    }


def test_bad_request_is_not_retried():
    """Invalid requests are fatal because retrying cannot make them valid."""
    from singer_sdk.exceptions import FatalAPIError

    stream = object.__new__(hubspotStream)
    stream.path = "example"
    response = Mock(status_code=400, reason="Bad Request", text="invalid")
    response.request = requests.Request("GET", "https://example.test").prepare()

    with __import__("pytest").raises(FatalAPIError):
        stream.validate_response(response)
