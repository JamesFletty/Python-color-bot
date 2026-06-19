"""Shim so the repo Alembic project directory can coexist with Alembic package imports."""

from __future__ import annotations

import site
from pathlib import Path

_current_dir = Path(__file__).resolve().parent
_real_init: Path | None = None
for _site_dir in site.getsitepackages() + [site.getusersitepackages()]:
    _candidate = Path(_site_dir) / "alembic" / "__init__.py"
    if _candidate.exists() and _candidate.resolve() != Path(__file__).resolve():
        _real_init = _candidate
        break

if _real_init is not None:
    __path__ = [str(_real_init.parent), str(_current_dir)]  # type: ignore[assignment]
    exec(compile(_real_init.read_text(encoding="utf-8"), str(_real_init), "exec"), globals())
else:
    __path__ = [str(_current_dir)]  # type: ignore[assignment]
