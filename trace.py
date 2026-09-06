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
    def __init__(self, trace_id=None, path=TRACE_FILE, on_event=None):
        self.id = trace_id or f"t_{uuid.uuid4().hex[:8]}"
        self.path = Path(path)
        self.step = 0
        self.started = time.time()
        # Optional callback fired with each record as it's emitted, e.g.
        # Trace(on_event=lambda rec: ...). Used by the UI to stream the
        # trace live instead of re-reading the file. Never allowed to break
        # the run: a broken callback should not take down the agent.
        self.on_event = on_event

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
        detail = " ".join(f"{k}={v}" for k, v in payload.items() if k not in ("text", "citations"))
        print(f"  [{record['elapsed_s']:>6.2f}s] {event:<22} {detail[:110]}")

        if self.on_event is not None:
            try:
                self.on_event(record)
            except Exception:
                pass

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