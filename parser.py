import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup


def parse_find_url(file: bytes | str, ext_list: list[str]) -> list[str]:
    soup = BeautifulSoup(file.lower(), "html.parser")
    ext_pattern = "|".join([f"\.{re.escape(ext)}" for ext in ext_list])
    pattern = re.compile(ext_pattern, re.IGNORECASE)
    urls = []
    for tag in soup.find_all(True):
        for attr in ["href", "src"]:
            if tag.has_attr(attr):
                url = tag[attr]
                if pattern.search(url):
                    urls.append(url)

    return urls


def parse_url(origin: str, url_path: str) -> str:
    if url_path.startswith("http://") or url_path.startswith("https://"):
        return url_path
    base = urlparse(origin)
    if not url_path.startswith("/"):
        url_path = "/" + url_path
    return f"{base.scheme}://{base.netloc}{url_path}"
