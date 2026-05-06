"""Wiki uploader: idempotent page writes against MediaWiki."""

from obelisk.upload.config import WikiConfig, load_config
from obelisk.upload.client import WikiClient

__all__ = ["WikiConfig", "load_config", "WikiClient"]
