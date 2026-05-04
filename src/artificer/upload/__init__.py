"""Wiki uploader: idempotent page writes against MediaWiki."""

from artificer.upload.config import WikiConfig, load_config
from artificer.upload.client import WikiClient

__all__ = ["WikiConfig", "load_config", "WikiClient"]
