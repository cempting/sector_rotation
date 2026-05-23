from sector_rotation.src.core.data.download_status import (
    clear_download_status,
    get_retry_after_seconds,
    get_download_status,
    is_download_blocked,
    record_download_failure,
    record_download_success,
)


def test_record_download_failure_marks_rate_limited():
    clear_download_status()

    record_download_failure("429 Too Many Requests: rate limit exceeded")
    status = get_download_status()

    assert status is not None
    assert status["level"] == "rate_limited"
    assert "Try again later" in str(status["message"])
    assert is_download_blocked("yfinance")
    assert int(status.get("retry_after_seconds", 0)) > 0
    assert get_retry_after_seconds("yfinance") > 0


def test_record_download_success_sets_ok_state():
    clear_download_status()

    record_download_success("Downloaded successfully")
    status = get_download_status()

    assert status is not None
    assert status["level"] == "ok"
    assert status["message"] == "Downloaded successfully"


def test_record_download_success_does_not_clear_recent_rate_limit():
    clear_download_status()

    record_download_failure("429 Too Many Requests")
    record_download_success("Downloaded successfully")
    status = get_download_status()

    assert status is not None
    assert status["level"] == "rate_limited"
