from dataclasses import dataclass
from datetime import datetime


@dataclass
class CrawlItem:
    title: str
    link: str
    source_url: str
    crawled_at: datetime
    