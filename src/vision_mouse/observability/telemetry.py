from __future__ import annotations

import json
import logging
import threading
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional

from vision_mouse.domain.vision import utc_now


@dataclass(frozen=True)
class MetricRecord:
    name: str
    value: float
    tags: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class LogEvent:
    level: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=utc_now)


class PipelineTelemetry:
    def __init__(self, logger_name: str = "vision_mouse", max_records: int = 500) -> None:
        self.logger = logging.getLogger(logger_name)
        self.metrics: deque[MetricRecord] = deque(maxlen=max_records)
        self.events: deque[LogEvent] = deque(maxlen=max_records)
        self._lock = threading.Lock()

    def record_metric(self, name: str, value: float, tags: Optional[dict[str, str]] = None) -> None:
        record = MetricRecord(name=name, value=value, tags=tags or {})
        with self._lock:
            self.metrics.append(record)
        self.logger.debug(json.dumps({"metric": asdict(record)}, default=str))

    def log_event(
        self,
        level: str,
        message: str,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        event = LogEvent(level=level, message=message, context=context or {})
        with self._lock:
            self.events.append(event)
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.log(log_level, json.dumps({"event": asdict(event)}, default=str))

    def snapshot(self) -> dict[str, list[dict[str, Any]]]:
        with self._lock:
            return {
                "metrics": [asdict(metric) for metric in self.metrics],
                "events": [asdict(event) for event in self.events],
            }
