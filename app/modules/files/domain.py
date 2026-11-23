"""The file life-cycle as a tiny state machine. Pure Python: easy to read, easy to test.

    pending -> uploaded -> processing -> ready
                              |  \\-> failed
    (anything that is not already deleted) -> deleted
"""

PENDING = "pending"        # record exists, client has not uploaded yet
UPLOADED = "uploaded"      # bytes are in MinIO, waiting for the processor
PROCESSING = "processing"  # processor worker is busy with it
READY = "ready"            # checksum + type detection done, can be shared
FAILED = "failed"
DELETED = "deleted"

TRANSITIONS: dict[str, set[str]] = {
    PENDING: {UPLOADED, DELETED},
    UPLOADED: {PROCESSING, DELETED},
    PROCESSING: {PROCESSING, READY, FAILED, DELETED},  # PROCESSING->PROCESSING = retry
    READY: {DELETED},
    FAILED: {DELETED},
    DELETED: set(),
}
TERMINAL = {READY, FAILED, DELETED}


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, set())


def allowed_from(target: str) -> set[str]:
    """Which states may move to `target`. The repo uses this to build an atomic compare-and-set."""
    return {state for state, targets in TRANSITIONS.items() if target in targets}
