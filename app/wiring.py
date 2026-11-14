"""Central place that attaches migrated routers to the FastAPI app.

``server.py`` calls :func:`include_migrated_routers` once, at the end of the module
(after every handler is defined).  To migrate another endpoint:

1. Remove its ``@app.<method>(...)`` decorator from ``server.py`` (keep the function).
2. Add its router here, passing the existing function as the callable.
3. Add the path to ``MIGRATED_PATHS`` so tests catch accidental duplicates.
"""

from typing import Any, Callable, Dict, List

from app.routers import discovery, status

# Paths now served by app/routers/*; server.py must no longer decorate these.
MIGRATED_PATHS: List[str] = [
    "/api/status/all",
    "/api/chat/context_usage",
    "/api/models/list",
]


def include_migrated_routers(app: Any, deps: Dict[str, Callable]) -> List[str]:
    """Attach migrated routers. ``deps`` maps names to existing server.py callables."""
    current_user = deps["current_user"]
    app.include_router(status.build_router(current_user, deps["status"]))
    app.include_router(discovery.build_router(current_user, deps["context_usage"], deps["models"]))
    return list(MIGRATED_PATHS)

