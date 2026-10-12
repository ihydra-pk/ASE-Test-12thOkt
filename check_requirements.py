"""Check every dependency in requirements.txt against the PyPI JSON API."""

import json
import re
import urllib.error
import urllib.parse
import urllib.request

REQUIREMENTS_FILE = "requirements.txt"
PYPI_URL = "https://pypi.org/pypi"


def fetch_json(url):
    """Return parsed JSON for url, or None if PyPI answers 404."""
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return None
        raise


def parse_line(line):
    """Return (name, pinned_version or None) for a requirement line, or None to skip it."""
    line = line.split("#", 1)[0].strip()
    if not line or line.startswith("-"):  # blank, comment, or pip option (-r, -e, ...)
        return None
    line = line.split(";", 1)[0].strip()  # drop environment markers
    match = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*(.*)$", line)
    if not match:
        return None
    name, spec = match.group(1), match.group(2).strip()
    pinned = re.fullmatch(r"==\s*([^\s,]+)", spec)
    return name, pinned.group(1) if pinned else None


def main():
    with open(REQUIREMENTS_FILE, encoding="utf-8") as f:
        deps = [d for d in (parse_line(line) for line in f) if d]

    missing_packages = []
    missing_versions = []
    oldest = None  # (upload_time, "name==version")

    for name, version in deps:
        quoted = urllib.parse.quote(name)
        if fetch_json(f"{PYPI_URL}/{quoted}/json") is None:
            missing_packages.append(name)
            continue
        if version is None:
            continue
        release = fetch_json(f"{PYPI_URL}/{quoted}/{urllib.parse.quote(version)}/json")
        if release is None:
            missing_versions.append(f"{name}=={version}")
            continue
        urls = release.get("urls") or []
        if not urls:
            continue
        upload_time = urls[0]["upload_time"]
        if oldest is None or upload_time < oldest[0]:
            oldest = (upload_time, f"{name}=={version}")

    print(f"Dependencies checked: {len(deps)}")
    print(f"Packages not on PyPi: {len(missing_packages)}")
    print(f"Versions not on PyPi: {len(missing_versions)}")
    if oldest:
        print(f"Oldest pinned release: {oldest[1]} ({oldest[0][:4]})")
    else:
        print("Oldest pinned release: none")


if __name__ == "__main__":
    main()
