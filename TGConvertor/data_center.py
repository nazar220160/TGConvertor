"""Telegram data-center endpoints used when a session has no stored address."""

from .exceptions import ValidationError


class DataCenter:
    TEST = {1: "149.154.175.10", 2: "149.154.167.40", 3: "149.154.175.117"}
    PROD = {
        1: "149.154.175.53",
        2: "149.154.167.51",
        3: "149.154.175.100",
        4: "149.154.167.91",
        5: "91.108.56.130",
        203: "91.105.192.100",
    }
    TEST_IPV6 = {
        1: "2001:b28:f23d:f001::e",
        2: "2001:67c:4e8:f002::e",
        3: "2001:b28:f23d:f003::e",
    }
    PROD_IPV6 = {
        1: "2001:b28:f23d:f001::a",
        2: "2001:67c:4e8:f002::a",
        3: "2001:b28:f23d:f003::a",
        4: "2001:67c:4e8:f004::a",
        5: "2001:b28:f23f:f005::a",
        203: "2a0a:f280:203:a:5000::100",
    }
    PROD_MEDIA = {2: "149.154.167.151", 4: "149.154.164.250"}
    PROD_IPV6_MEDIA = {2: "2001:67c:4e8:f002::b", 4: "2001:67c:4e8:f004::b"}

    def __new__(
        cls, dc_id: int, test_mode: bool = False, ipv6: bool = False, media: bool = False
    ) -> tuple[str, int]:
        endpoints = (
            (cls.TEST_IPV6 if ipv6 else cls.TEST)
            if test_mode
            else (cls.PROD_IPV6 if ipv6 else cls.PROD)
        )
        if media and not test_mode:
            endpoints = endpoints | (cls.PROD_IPV6_MEDIA if ipv6 else cls.PROD_MEDIA)
        try:
            return endpoints[dc_id], 80 if test_mode else 443
        except KeyError:
            raise ValidationError(
                f"Unknown data center {dc_id}; provide server_address explicitly"
            ) from None
