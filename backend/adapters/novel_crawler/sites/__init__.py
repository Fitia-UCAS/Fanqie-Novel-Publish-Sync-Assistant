from __future__ import annotations

from backend.adapters.novel_crawler.sites.lanmeiwen import LanmeiwenAdapter
from backend.adapters.novel_crawler.sites.renrenreshu import RenrenreshuAdapter
from backend.adapters.novel_crawler.sites.xsbook import XsbookAdapter
from backend.adapters.novel_crawler.sites.site_adapter import NovelSiteAdapter
from backend.adapters.novel_crawler.sites.site_registry import ADAPTER_TYPES, adapter_for_url, supported_sites

__all__ = [
    "ADAPTER_TYPES",
    "LanmeiwenAdapter",
    "XsbookAdapter",
    "NovelSiteAdapter",
    "RenrenreshuAdapter",
    "adapter_for_url",
    "supported_sites",
]
