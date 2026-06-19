"""
EDM v2 — Feature Flags System (Phase 5: Production Hardening).

Simple toggle‑based feature flags that can be configured via environment
variables or the Settings object.  This allows gradual rollout of new
features without code changes.

Usage::

    from app.services.feature_flags import FF

    if FF.enabled("bulk_export_v2"):
        # new code path
    else:
        # old code path

Flags can be toggled at startup via environment variables::

    FEATURE_BULK_EXPORT_V2=true
    FEATURE_NEW_DASHBOARD=true
"""

import os
import logging
from typing import Optional

logger = logging.getLogger("edm.feature_flags")


class FeatureFlags:
    """Feature flag registry backed by environment variables.

    All flags default to *False* unless explicitly enabled.  To add a new
    flag, simply use ``FF.enabled("my_feature")`` anywhere in the codebase.
    The flag is then controlled by the env var ``FEATURE_MY_FEATURE=true``.

    For consistency, document permanent flags in this docstring or in the
    project configuration.
    """

    # ── Permanent flags (documented) ──────────────────────────────
    # Naming convention: ``FEATURE_<UPPERCASE_NAME>``

    # Feature name → env var key
    _FLAG_ENV_PREFIX = "FEATURE_"

    def enabled(self, name: str) -> bool:
        """Check whether a feature flag is enabled.

        Parameters
        ----------
        name:
            Feature name in ``snake_case`` (e.g. ``bulk_export_v2``).

        Returns
        -------
        ``True`` if the env var ``FEATURE_<UPPERCASE_NAME>`` is set to
        ``"true"``, ``"1"``, or ``"yes"``.
        """
        env_key = self._to_env_key(name)
        value = os.getenv(env_key, "").strip().lower()
        enabled = value in ("true", "1", "yes")
        return enabled

    def _to_env_key(self, name: str) -> str:
        """Convert ``snake_case`` to ``FEATURE_UPPER_CASE``."""
        return f"{self._FLAG_ENV_PREFIX}{name.upper()}"

    def enable(self, name: str) -> None:
        """Programmatically enable a feature flag for the current process."""
        os.environ[self._to_env_key(name)] = "true"
        logger.info("Feature flag '%s' enabled", name)

    def disable(self, name: str) -> None:
        """Programmatically disable a feature flag for the current process."""
        os.environ[self._to_env_key(name)] = "false"
        logger.info("Feature flag '%s' disabled", name)

    def list_all(self) -> list[dict]:
        """List all known feature flags and their current state."""
        flags = []
        for key, value in sorted(os.environ.items()):
            if key.startswith(self._FLAG_ENV_PREFIX):
                flags.append({
                    "name": key.removeprefix(self._FLAG_ENV_PREFIX).lower(),
                    "env_var": key,
                    "value": value.strip().lower() in ("true", "1", "yes"),
                })
        return flags


# Global singleton — import this directly
FF = FeatureFlags()
