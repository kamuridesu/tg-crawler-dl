from urllib.parse import urlparse
from bs4 import BeautifulSoup
import re


def parse_find_url(file: bytes | str, ext_list: list[str]) -> list[str]:
    # Parse the HTML content
    soup = BeautifulSoup(file, 'html.parser')
    
    # Create a regex pattern for the extensions
    ext_pattern = '|'.join([f'\.{re.escape(ext)}$' for ext in ext_list])
    pattern = re.compile(ext_pattern, re.IGNORECASE)

    # Find all tags with attributes that may contain URLs (e.g., href, src)
    urls = []
    for tag in soup.find_all(True):  # True finds all tags
        for attr in ['href', 'src']:
            if tag.has_attr(attr):
                url = tag[attr]
                if pattern.search(url):  # Check if the URL ends with one of the extensions
                    urls.append(url)

    return urls


def parse_url(origin: str, url_path: str) -> str:
    if url_path.startswith("http://") and url_path.startswith("https://"):
        return url_path
    base = urlparse(origin)
    if not url_path.startswith("/"):
        url_path = "/" + url_path
    return f"{base.scheme}://{base.netloc}{url_path}"
