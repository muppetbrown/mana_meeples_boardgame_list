"""
API versioning configuration.
Implements version-based routing with backward compatibility.
"""
from typing import Literal

# Current API version
CURRENT_API_VERSION = "v1"

# Supported API versions
SUPPORTED_VERSIONS = ["v1"]

# API version type
APIVersion = Literal["v1"]


def get_version_prefix(version: str = CURRENT_API_VERSION) -> str:
    """
    Get the API prefix for a specific version.

    Args:
        version: API version (default: current version)

    Returns:
        Version prefix string (e.g., "/api/v1")

    Raises:
        ValueError: If version is not supported
    """
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(
            f"Unsupported API version: {version}. Supported versions: {SUPPORTED_VERSIONS}"
        )
    return f"/api/{version}"


def get_legacy_prefix() -> str:
    """
    Get the legacy API prefix (for backward compatibility).
    Legacy endpoints are mapped to the current API version.

    Returns:
        Legacy prefix string ("/api")
    """
    return "/api"


class APIVersionInfo:
    """API version information for clients"""

    def __init__(self):
        self.current = CURRENT_API_VERSION
        self.supported = SUPPORTED_VERSIONS
        self.deprecated = []  # Currently no deprecated versions

    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            "current_version": self.current,
            "supported_versions": self.supported,
            "deprecated_versions": self.deprecated,
            "version_prefix_format": "/api/{version}",
            "legacy_prefix": "/api (maps to /api/v1)",
        }


# Singleton instance
version_info = APIVersionInfo()
