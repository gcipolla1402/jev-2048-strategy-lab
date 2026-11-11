from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Metrics:
    total_jev_calls: int = 0
    successful_moves: int = 0
    api_errors: int = 0
    total_latency_ms: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_request_bytes: int = 0

    @property
    def average_latency_ms(self) -> float | None:
        if self.total_jev_calls == 0:
            return None
        return round(self.total_latency_ms / self.total_jev_calls, 1)

    @property
    def average_request_bytes(self) -> float | None:
        if self.total_jev_calls == 0:
            return None
        return round(self.total_request_bytes / self.total_jev_calls, 1)

    def record_call(
        self,
        latency_ms: float,
        input_tokens: int | None,
        output_tokens: int | None,
        request_bytes: int = 0,
    ) -> None:
        self.total_jev_calls += 1
        self.total_latency_ms += latency_ms
        self.total_input_tokens += input_tokens or 0
        self.total_output_tokens += output_tokens or 0
        self.total_request_bytes += request_bytes

