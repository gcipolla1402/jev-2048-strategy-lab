from app.metrics import Metrics


def test_metrics_preserve_latency_tokens_and_request_size():
    metrics = Metrics()
    metrics.record_call(100, 12, 3, 400)
    metrics.record_call(200, 18, 4, 800)
    assert metrics.total_jev_calls == 2
    assert metrics.average_latency_ms == 150
    assert metrics.total_input_tokens == 30
    assert metrics.total_output_tokens == 7
    assert metrics.average_request_bytes == 600
