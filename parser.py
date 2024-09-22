import re

url_pattern = re.compile(
    r"(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})"
)


ANTI_PATTERNS = [
    '">',
    "/>",
    ">",
    "')",
    "/>",
    "&quot",
    '",',
    '"}',
    '"\\',
    "+e," r"\u003c",
    r"\u003e",
    "&gt",
    "</",
]


def parse_find_url(file: bytes, ext_list: list[str]) -> list[str]:
    content = file.decode()
    all_urls = []
    url_pattern = re.compile(
        r"(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})"
    )
    for line in content.splitlines():
        urls: list[str] = url_pattern.findall(line)
        if urls:
            for url in urls:
                for u in ANTI_PATTERNS:
                    if u in url:
                        url = url.split(u)[0]
                url = url.strip('"')
                url = url.strip(")")
                url = url.strip("\\")
                url = url.strip("'")
                if any([url.endswith(x) for x in ext_list]):
                    if url not in all_urls:
                        all_urls.append(url)
    return all_urls
