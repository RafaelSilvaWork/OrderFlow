from modules.coupa_scraper import _describe_network_error


def test_recognizes_dns_failure():
    msg = _describe_network_error(Exception("net::ERR_NAME_NOT_RESOLVED at https://empresa.coupahost.com/"))

    assert msg is not None
    assert "internet" in msg.lower() or "url" in msg.lower()


def test_recognizes_connection_refused():
    msg = _describe_network_error(Exception("net::ERR_CONNECTION_REFUSED at https://empresa.coupahost.com/"))

    assert msg is not None
    assert "coupa" in msg.lower()


def test_recognizes_navigation_timeout():
    msg = _describe_network_error(Exception("Timeout 30000ms exceeded while navigating to https://empresa.coupahost.com/"))

    assert msg is not None
    assert "timeout" in msg.lower() or "demorou" in msg.lower()


def test_returns_none_for_unrelated_error():
    assert _describe_network_error(Exception("Element not found: .po-number")) is None
