from __future__ import annotations

import os

__version__ = "0.1.0"
__build_time__ = os.environ.get("ORGANIZER_BUILD_TIME", "unknown")

__all__ = ["__version__", "__build_time__"]
