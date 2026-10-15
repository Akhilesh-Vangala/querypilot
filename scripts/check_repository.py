"""Check owned docs, local media and the explicit frontend/backend layout."""

from html.parser import HTMLParser
from pathlib import Path
import re
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def slug(text):
    text = re.sub(r"<[^>]*>", "", text).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text, flags=re.UNICODE)
    return text.replace(" ", "-")


def anchors(path):
    body = path.read_text()
    body = re.sub(r"```[\s\S]*?```", "", body)
    result = set(re.findall(r'<a\s+id=["\']([^"\']+)', body))
    used = {}
    for title in re.findall(r"^#{1,6}\s+(.+)$", body, re.MULTILINE):
        name = slug(title)
        count = used.get(name, 0)
        result.add(name + ("-" + str(count) if count else ""))
        used[name] = count + 1
    return result


class Media(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attributes):
        for key, value in attributes:
            if value and key in ("src", "srcset", "poster"):
                self.targets.append(value)


def main():
    assert (ROOT / "backend").is_dir()
    assert (ROOT / "frontend").is_dir()
    for name in ("HANDOFF", "PLAN", "PROGRESS"):
        assert (ROOT / "docs/project" / (name + ".md")).is_file()
        assert not (ROOT / (name + ".md")).exists(), (
            "Project history belongs in docs/project"
        )
    files = list(ROOT.glob("*.md")) + list((ROOT / "docs").rglob("*.md"))
    files += list((ROOT / "backend").glob("*.md")) + list(
        (ROOT / "frontend").glob("*.md")
    )
    capture = ROOT / "docs/demos/interactive-recording.json"
    manifest = json.loads(capture.read_text())
    assert len(manifest["frames"]) == 6
    video = ROOT / manifest["video_path"]
    assert video.stat().st_size < 4_000_000
    assert hashlib.sha256(video.read_bytes()).hexdigest() == manifest["video_sha256"]
    for name, digest in manifest["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, "Capture source changed: " + name
    errors, count = [], 0
    for path in files:
        body = path.read_text()
        targets = re.findall(r"\]\(([^\s)]+)\)", body)
        parser = Media()
        parser.feed(body)
        targets += parser.targets
        for target in targets:
            if "://" in target or target.startswith(("mailto:", "data:", "/")):
                continue
            location, _, fragment = target.partition("#")
            destination = (path.parent / location).resolve() if location else path
            if "artifacts/generated/" in target or ".tools/" in target or "__pycache__/" in target:
                errors.append(str(path.relative_to(ROOT)) + ": link points to ignored local state " + target)
                continue
            if not destination.exists():
                errors.append(str(path.relative_to(ROOT)) + ": missing " + target)
            elif (
                fragment
                and destination.suffix == ".md"
                and not re.match(r"L\d+", fragment)
            ):
                if fragment not in anchors(destination):
                    errors.append(
                        str(path.relative_to(ROOT)) + ": missing anchor " + target
                    )
            count += 1
    for token in ("TBD", "TODO", "YOUR_API_KEY", "localhost:1234"):
        assert token not in (ROOT / "README.md").read_text(), (
            "Unfinished README: " + token
        )
    if errors:
        raise SystemExit("\n".join(errors))
    print(
        "Repository layout and "
        + str(count)
        + " local documentation/media references pass."
    )


if __name__ == "__main__":
    main()
