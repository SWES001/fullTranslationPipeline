from dataclasses import dataclass, field
from time import perf_counter


@dataclass
class SegmentTimer:
    segment_id: str
    marks: dict[str, float] = field(default_factory=dict)

    def mark(self, name: str) -> None:
        self.marks[name] = perf_counter()

    def durations_ms(self) -> dict[str, float]:
        ordered = list(self.marks.items())
        return {
            f"{prev_name}_to_{next_name}": round((next_time - prev_time) * 1000, 1)
            for (prev_name, prev_time), (next_name, next_time) in zip(ordered, ordered[1:])
        }
