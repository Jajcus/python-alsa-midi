
import pytest

from alsa_midi import RealTime


def test_construct_int():
    value = RealTime(99999)
    assert value.seconds == 99999
    assert value.nanoseconds == 0


def test_construct_int_int():
    value = RealTime(99999, 222222222)
    assert value.seconds == 99999
    assert value.nanoseconds == 222222222


def test_construct_float():
    value = RealTime(2.00022)
    assert value.seconds == 2
    assert value.nanoseconds / 1000000000 == pytest.approx(0.00022)


def test_construct_str():
    value = RealTime("99999")
    assert value.seconds == 99999
    assert value.nanoseconds == 0

    value = RealTime("12345.678")
    assert value.seconds + value.nanoseconds / 1000000000 == pytest.approx(12345.678)


def test_repr():
    value = RealTime(1234, 5678)
    assert repr(value) == "RealTime(seconds=1234, nanoseconds=5678)"


def test_str():
    value = RealTime(0)
    assert str(value) == "0.000000000"
    value = RealTime(1, 1)
    assert str(value) == "1.000000001"
    value = RealTime(999999999, 999999999)
    assert str(value) == "999999999.999999999"


def test_int():
    value = RealTime(0)
    assert int(value) == 0
    value = RealTime(1234, 5678)
    assert int(value) == 1234


def test_float():
    value = RealTime(0)
    assert int(value) == 0.0
    value = RealTime(1234, 5678)
    assert float(value) == pytest.approx(1234.000005678)


def test_negative():
    with pytest.raises(ValueError):
        RealTime(-1)
    with pytest.raises(ValueError):
        RealTime(0, -1)


def test_compare():
    assert RealTime(1, 2) == RealTime(1, 2)
    assert RealTime(1, 2) != RealTime(3, 4)
    assert RealTime(1, 2) < RealTime(3, 4)
    assert RealTime(5, 6) > RealTime(3, 4)  # type: ignore
    assert RealTime(1, 2) <= RealTime(3, 4)  # type: ignore
    assert RealTime(5, 6) >= RealTime(3, 4)  # type: ignore
    assert RealTime(1, 2) <= RealTime(1, 2)  # type: ignore
    assert RealTime(1, 2) >= RealTime(1, 2)  # type: ignore
