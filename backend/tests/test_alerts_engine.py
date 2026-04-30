"""
Tests for the alerts pure-logic evaluator.

These cover the `should_fire` function in `app.routes.alerts` — the only
piece that actually decides when a server-side alert triggers. Network
calls and DB operations are tested separately via integration tests.
"""

import pytest

from app.routes.alerts import should_fire


@pytest.mark.parametrize(
    "kind,threshold,price,rsi,expected",
    [
        # 'above'
        ("above", 1500, 1500, None, True),
        ("above", 1500, 1500.01, None, True),
        ("above", 1500, 1499.99, None, False),
        ("above", 1500, None, None, False),

        # 'below'
        ("below", 3000, 3000, None, True),
        ("below", 3000, 2999, None, True),
        ("below", 3000, 3001, None, False),

        # 'rsi_above'
        ("rsi_above", 70, None, 71, True),
        ("rsi_above", 70, None, 70, True),
        ("rsi_above", 70, None, 69.9, False),
        ("rsi_above", 70, None, None, False),

        # 'rsi_below'
        ("rsi_below", 30, None, 29.9, True),
        ("rsi_below", 30, None, 30.1, False),

        # Unknown kinds never fire
        ("unknown", 1, 100, 100, False),
        ("", 1, 100, 100, False),
    ],
)
def test_should_fire(kind, threshold, price, rsi, expected):
    assert should_fire(kind, threshold, price=price, rsi=rsi) is expected


def test_should_fire_ignores_unrelated_value():
    # 'above' must not fire just because rsi is high
    assert should_fire("above", 1500, price=None, rsi=99) is False
    # 'rsi_below' must not fire just because price is low
    assert should_fire("rsi_below", 30, price=1, rsi=None) is False
