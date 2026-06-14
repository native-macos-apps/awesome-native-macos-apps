from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
OUTPUT = ROOT / "data" / "apps.yaml"

PRICE_LABELS = {
    "free": "free",
    "freemium": "freemium",
    "paid": "paid",
    "subscription": "paid",
    "one-time subscription": "paid",
}


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def parse_readme() -> list[dict]:
    categories: list[dict] = []
    current: dict | None = None

    app_re = re.compile(r"^- \[(?P<name>.+?)\]\((?P<url>.+?)\) - (?P<rest>.+)$")

    for raw_line in README.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if line.startswith("## "):
            name = line[3:].strip()
            current = {
                "id": slugify(name),
                "name": name,
                "description": f"Native macOS apps for {name.lower()}.",
                "apps": [],
            }
            categories.append(current)
            continue

        if current is None or not line.startswith("- ["):
            continue

        match = app_re.match(line)
        if not match:
            continue

        rest = match.group("rest").strip()
        labels = [label.strip() for label in re.findall(r"`([^`]+)`", rest)]
        description = re.sub(r"\s*`[^`]+`", "", rest).strip()
        description = description.rstrip(".")

        normalized_labels = [label.lower() for label in labels]
        price = "free"
        for label in normalized_labels:
            if label in PRICE_LABELS:
                price = PRICE_LABELS[label]
                break

        tags = []
        for part in current["id"].split("-"):
            if part and part not in {"and"}:
                tags.append(part)
        for label in normalized_labels:
            if label not in PRICE_LABELS:
                tags.append(slugify(label))

        deduped_tags = []
        for tag in tags:
            if tag and tag not in deduped_tags:
                deduped_tags.append(tag)

        app = {
            "name": match.group("name").strip(),
            "description": description,
            "url": match.group("url").strip(),
            "tags": deduped_tags,
            "price": price,
            "status": "active",
        }

        if "open source" in normalized_labels:
            app["license"] = "Open Source"

        current["apps"].append(app)

    return categories


def write_yaml(categories: list[dict]) -> None:
    lines = ["categories:"]
    for category in categories:
        lines.extend(
            [
                f"  - id: {category['id']}",
                f"    name: {yaml_quote(category['name'])}",
                f"    description: {yaml_quote(category['description'])}",
                "    apps:",
            ]
        )
        for app in category["apps"]:
            tags = ", ".join(app["tags"])
            lines.extend(
                [
                    f"      - name: {yaml_quote(app['name'])}",
                    f"        description: {yaml_quote(app['description'])}",
                    f"        url: {yaml_quote(app['url'])}",
                    f"        tags: [{tags}]",
                ]
            )
            if "license" in app:
                lines.append(f"        license: {yaml_quote(app['license'])}")
            lines.extend(
                [
                    f"        price: {app['price']}",
                    f"        status: {app['status']}",
                ]
            )

    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write_yaml(parse_readme())
