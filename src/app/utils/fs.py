from pathlib import Path
import os
import tempfile


def atomic_write(path: Path, data: str):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=path.name,
        text=True,
    )

    try:
        with os.fdopen(fd, "w") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_path, path)  # ATOMIC
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
