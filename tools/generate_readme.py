from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "apps.yaml"
README = ROOT / "README.md"


def unquote(value: str) -> str:
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
        value = value.replace('\\"', '"').replace("\\\\", "\\")
    return value


def parse_value(value: str):
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [] if not inner else [part.strip() for part in inner.split(",")]
    if re.fullmatch(r"\d+", value):
        return int(value)
    return unquote(value)


def load_apps_yaml() -> list[dict]:
    categories: list[dict] = []
    current_category: dict | None = None
    current_app: dict | None = None

    for raw_line in DATA.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.strip() == "categories:":
            continue

        stripped = raw_line.strip()
        indent = len(raw_line) - len(raw_line.lstrip(" "))

        if indent == 2 and stripped.startswith("- "):
            current_category = {}
            current_app = None
            categories.append(current_category)
            key, value = stripped[2:].split(":", 1)
            current_category[key] = parse_value(value)
            continue

        if indent == 4 and current_category is not None:
            key, value = stripped.split(":", 1)
            if key == "apps":
                current_category["apps"] = []
            else:
                current_category[key] = parse_value(value)
            continue

        if indent == 6 and current_category is not None and stripped.startswith("- "):
            current_app = {}
            current_category.setdefault("apps", []).append(current_app)
            key, value = stripped[2:].split(":", 1)
            current_app[key] = parse_value(value)
            continue

        if indent == 8 and current_app is not None:
            key, value = stripped.split(":", 1)
            current_app[key] = parse_value(value)

    return categories


def github_anchor(text: str) -> str:
    text = text.lower()
    result = []
    for c in text:
        if c.isalnum() or c in " -_":
            result.append(c)
    text = "".join(result)
    text = text.replace(" ", "-")
    return text


def get_labels(app: dict) -> list[str]:
    labels = []
    price = app.get("price", "free")
    
    # Map subscription apps back to their original labels
    subscription_apps = {"Fantastical", "Paste", "Sketch", "Copilot", "Ulysses"}
    if app["name"] in subscription_apps:
        labels.append("Subscription")
    elif app["name"] == "Speakmac":
        labels.append("One-Time Subscription")
    else:
        labels.append(price.capitalize())

    if app.get("license") == "Open Source":
        labels.append("Open Source")

    if "eu" in app.get("tags", []):
        labels.append("EU")

    return labels


def generate_readme_content(categories: list[dict]) -> str:
    lines = [
        "# Awesome Native macOS Apps",
        "",
        "In recent years, many desktop applications have shifted towards web-based technologies like Electron, wrapping web apps inside heavy webview shells. While this simplifies cross-platform development, it often leads to bloated file sizes, high memory consumption, sluggish performance, and a user interface that lacks the native feel and integration of macOS.",
        "",
        "This project is a curated library of **native macOS applications**—built using native APIs and frameworks like Swift, Objective-C, and AppKit/SwiftUI. Our goal is to help you discover and choose fast, lightweight, and energy-efficient apps that look and feel right at home on your Mac.",
        "",
        "---",
        "",
        "**Categories**",
    ]

    for category in categories:
        anchor = github_anchor(category["name"])
        lines.append(f"- [{category['name']}](#{anchor})")

    lines.extend([
        "",
        "---",
        "",
    ])

    for category in categories:
        lines.append(f"## {category['name']}")
        lines.append("")
        for app in category.get("apps", []):
            desc = app["description"].strip()
            if not desc.endswith("."):
                desc += "."
            labels = get_labels(app)
            label_str = " ".join(f"`{l}`" for l in labels)
            if label_str:
                lines.append(f"- [{app['name']}]({app['url']}) - {desc} {label_str}")
            else:
                lines.append(f"- [{app['name']}]({app['url']}) - {desc}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    categories = load_apps_yaml()
    # Sort apps within categories alphabetically by name
    for category in categories:
        if "apps" in category:
            category["apps"].sort(key=lambda x: x["name"].lower())
            
    content = generate_readme_content(categories)
    README.write_text(content, encoding="utf-8")
    print("README.md generated successfully!")


if __name__ == "__main__":
    main()
