"""
Append-only event log.

Every layer writes here. The UI is a view onto this file, not a separate
state store, so the trace a judge inspects and the trace we debug with are
the same artifact.
"""

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

TRACE_FILE = Path("trace.jsonl")


class Trace:
    def __init__(self, trace_id=None, path=TRACE_FILE):
        self.id = trace_id or f"t_{uuid.uuid4().hex[:8]}"
        self.path = Path(path)
        self.step = 0
        self.started = time.time()

    def emit(self, event, **payload):
        self.step += 1
        record = {
            "trace_id": self.id,
            "step": self.step,
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "elapsed_s": round(time.time() - self.started, 2),
            "event": event,
        }
        record.update(payload)

        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # Console view. The UI will read the file instead.
        detail = " ".join(f"{k}={v}" for k, v in payload.items() if k != "text")
        print(f"  [{record['elapsed_s']:>6.2f}s] {event:<22} {detail[:110]}")
        return record

    @staticmethod
    def read(trace_id, path=TRACE_FILE):
        """Return every event for one trace, in order."""
        path = Path(path)
        if not path.exists():
            return []
        out = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("trace_id") == trace_id:
                    out.append(rec)
        return out