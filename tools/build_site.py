from __future__ import annotations

import html
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "apps.yaml"
OUT_DIR = ROOT / "_site"


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


def get_icon_url(app: dict) -> str:
    if "icon" in app and app["icon"]:
        return app["icon"]
    url = app.get("url", "")
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Handle GitHub URLs specially - get repo avatar instead of generic GitHub icon
        if domain in ("github.com", "www.github.com"):
            # Extract owner and repo from GitHub URL
            path_parts = parsed.path.strip("/").split("/")
            if len(path_parts) >= 2:
                owner = path_parts[0]
                repo = path_parts[1]
                # Use GitHub's user/org avatar endpoint
                return f"https://avatars.githubusercontent.com/{owner}?s=128&v=4"
        
        if domain.startswith("www."):
            domain = domain[4:]
        if domain:
            return f"https://www.google.com/s2/favicons?sz=128&domain={domain}"
    except Exception:
        pass
    return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%230a7cff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='3' y='3' width='18' height='18' rx='2' ry='2'%3E%3C/rect%3E%3C/svg%3E"


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


def render(categories: list[dict]) -> str:
    app_count = sum(len(category.get("apps", [])) for category in categories)
    filter_options = [
        ("free", "Free"),
        ("freemium", "Freemium"),
        ("paid", "Paid"),
        ("open-source", "Open Source"),
    ]
    category_filters = "\n".join(
        f'<button class="category-button" type="button" data-category-filter="{html.escape(category["id"])}" aria-pressed="false">{html.escape(category["name"])}</button>'
        for category in categories
    )
    filters = "\n".join(
        f'<button class="filter-button" type="button" data-filter="{html.escape(value)}" aria-pressed="false">{html.escape(label)}</button>'
        for value, label in filter_options
    )

    sections = []
    for category in categories:
        cards = []
        for app in category.get("apps", []):
            tags = "".join(
                f'<span class="tag">{html.escape(str(tag))}</span>'
                for tag in app.get("tags", [])
            )
            license_label = app.get("license")
            license_html = (
                f'<span class="meta">{html.escape(str(license_label))}</span>'
                if license_label
                else ""
            )
            app_tags = " ".join(str(tag) for tag in app.get("tags", []))
            app_price = str(app.get("price", "free"))
            is_open_source = str(license_label).lower() == "open source"
            icon_url = get_icon_url(app)
            cards.append(
                f"""
                <article class="app-card" data-tags="{html.escape(app_tags)}" data-category-id="{html.escape(category['id'])}" data-price="{html.escape(app_price)}" data-open-source="{str(is_open_source).lower()}">
                  <div class="app-header">
                    <img class="app-icon" src="{html.escape(icon_url)}" alt="{html.escape(app['name'])} icon" width="36" height="36" loading="lazy" onerror="this.onerror=null; this.src=&quot;data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%230a7cff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='3' y='3' width='18' height='18' rx='2' ry='2'%3E%3C/rect%3E%3C/svg%3E&quot;;" />
                    <div class="app-title-wrapper">
                      <div class="app-title">
                        <a href="{html.escape(app['url'])}" rel="noopener noreferrer">{html.escape(app['name'])}</a>
                        <span class="price">{html.escape(app.get('price', 'free'))}</span>
                      </div>
                    </div>
                  </div>
                  <p>{html.escape(app['description'])}.</p>
                  <div class="meta-row">
                    <span class="meta">{html.escape(app.get('status', 'active'))}</span>
                    {license_html}
                  </div>
                  <div class="tags">{tags}</div>
                </article>
                """
            )

        sections.append(
            f"""
            <section id="{html.escape(category['id'])}" data-category>
              <div class="section-heading">
                <h2>{html.escape(category['name'])}</h2>
                <span data-section-count>{len(category.get('apps', []))} apps</span>
              </div>
              <p class="section-description">{html.escape(category.get('description', ''))}</p>
              <div class="grid">{''.join(cards)}</div>
            </section>
            """
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Awesome Native macOS Apps</title>
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #f7f8fb;
      --text: #15171c;
      --muted: #5d6575;
      --line: #d8dde8;
      --card: #ffffff;
      --accent: #0a7cff;
      --tag: #eef3f8;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #101217;
        --text: #f2f4f8;
        --muted: #a9b1c1;
        --line: #29303d;
        --card: #171b22;
        --accent: #5aa7ff;
        --tag: #222a35;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }}
    header, main {{
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
    }}
    header {{ padding: 56px 0 28px; }}
    h1 {{ margin: 0 0 12px; font-size: clamp(2rem, 4vw, 4.5rem); line-height: 1.02; letter-spacing: 0; }}
    header p {{ max-width: 820px; color: var(--muted); font-size: 1.08rem; }}
    .stats {{ display: flex; gap: 16px; flex-wrap: wrap; margin-top: 24px; color: var(--muted); }}
    nav {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 28px 0 4px; }}
    nav a, .category-button, .tag, .meta, .price, .filter-button {{
      background: transparent;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--muted);
      cursor: pointer;
      display: inline-flex;
      font: inherit;
      font-size: 0.82rem;
      padding: 4px 10px;
      text-decoration: none;
      white-space: nowrap;
    }}
    nav a:hover, .category-button:hover, .category-button[aria-pressed="true"], .filter-button:hover, .filter-button[aria-pressed="true"] {{
      border-color: var(--accent);
      color: var(--accent);
    }}
    .filters {{
      border-top: 1px solid var(--line);
      margin-top: 28px;
      padding-top: 20px;
    }}
    .filter-header {{
      align-items: center;
      display: flex;
      gap: 12px;
      justify-content: space-between;
      margin-bottom: 12px;
    }}
    .filter-header strong {{ font-size: 0.95rem; }}
    .filter-header span {{ color: var(--muted); font-size: 0.9rem; }}
    .filter-buttons {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    section {{ border-top: 1px solid var(--line); padding: 34px 0; }}
    .section-heading {{ align-items: baseline; display: flex; gap: 12px; justify-content: space-between; }}
    h2 {{ font-size: 1.45rem; margin: 0; }}
    .section-heading span, .section-description {{ color: var(--muted); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 12px;
      margin-top: 16px;
    }}
    .app-card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 8px;
      min-height: 190px;
      padding: 16px;
      display: flex;
      flex-direction: column;
    }}
    .app-header {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }}
    .app-icon {{
      border-radius: 22%;
      border: 1px solid var(--line);
      background: var(--card);
      height: 36px;
      width: 36px;
      object-fit: contain;
      padding: 4px;
      flex-shrink: 0;
      box-shadow: 0 2px 4px rgba(0,0,0,0.02);
      transition: transform 0.2s ease;
    }}
    .app-card:hover .app-icon {{
      transform: scale(1.05);
    }}
    .app-title-wrapper {{
      display: flex;
      flex-direction: column;
      flex: 1;
      min-width: 0;
    }}
    .app-title {{
      align-items: center;
      display: flex;
      gap: 8px;
      justify-content: space-between;
      width: 100%;
    }}
    .app-title a {{
      color: var(--text);
      font-size: 1.05rem;
      font-weight: 700;
      text-decoration: none;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .app-title a:hover {{ color: var(--accent); }}
    .price {{
      color: var(--accent);
      text-transform: capitalize;
      font-size: 0.78rem;
      font-weight: 600;
      background: rgba(10, 124, 255, 0.08);
      padding: 2px 8px;
      border-radius: 999px;
    }}
    @media (prefers-color-scheme: dark) {{
      .price {{
        background: rgba(90, 167, 255, 0.12);
      }}
    }}
    .app-card p {{
      color: var(--muted);
      margin: 0 0 16px 0;
      font-size: 0.92rem;
      flex-grow: 1;
    }}
    .meta-row, .tags {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .tags {{ margin-top: 12px; }}
    .tag {{ background: var(--tag); border: none; font-size: 0.78rem; font-weight: 500; }}
    [hidden] {{ display: none !important; }}
    footer {{ color: var(--muted); padding: 32px 0 56px; text-align: center; }}
  </style>
</head>
<body>
  <header>
    <h1>Awesome Native macOS Apps</h1>
    <p>A curated collection of macOS apps that prioritize a native Mac experience, thoughtful system integration, and everyday performance. Too many desktop apps now ship as heavy webview wrappers, often bringing larger downloads, higher memory use, slower launches, and interfaces that feel out of place on macOS.</p>
    <div class="stats">
      <span><span id="visible-count">{app_count}</span> apps</span>
      <span>{len(categories)} categories</span>
      <span>Generated from data/apps.yaml</span>
    </div>
    <nav aria-label="Filter apps by category">{category_filters}</nav>
    <div class="filters" aria-label="Filter apps">
      <div class="filter-header">
        <strong>Filter</strong>
        <span id="active-filter">No filter selected</span>
      </div>
      <div class="filter-buttons">
        {filters}
      </div>
    </div>
  </header>
  <main>{''.join(sections)}</main>
  <footer>Built with GitHub Actions and GitHub Pages.</footer>
  <script>
    const appCards = Array.from(document.querySelectorAll(".app-card"));
    const categorySections = Array.from(document.querySelectorAll("[data-category]"));
    const categoryButtons = Array.from(document.querySelectorAll("[data-category-filter]"));
    const filterButtons = Array.from(document.querySelectorAll("[data-filter]"));
    const visibleCount = document.querySelector("#visible-count");
    const activeFilter = document.querySelector("#active-filter");
    const filters = {json.dumps([value for value, _label in filter_options])};
    const categories = {json.dumps([category["id"] for category in categories])};
    const selectedFilters = new Set();
    const selectedCategories = new Set();

    function pluralizeApps(count) {{
      return count === 1 ? "1 app" : `${{count}} apps`;
    }}

    function syncUrl() {{
      const selectedFilterList = Array.from(selectedFilters);
      const selectedCategoryList = Array.from(selectedCategories);
      const params = new URLSearchParams();
      if (selectedFilterList.length > 0) {{
        params.set("filters", selectedFilterList.map((filter) => encodeURIComponent(filter)).join(","));
      }}
      if (selectedCategoryList.length > 0) {{
        params.set("categories", selectedCategoryList.map((category) => encodeURIComponent(category)).join(","));
      }}
      const hash = params.toString();
      history.replaceState(null, "", hash ? `#${{hash}}` : window.location.pathname + window.location.search);
    }}

    function matchesFilter(card, filter) {{
      if (filter === "open-source") {{
        return card.dataset.openSource === "true";
      }}
      return card.dataset.price === filter;
    }}

    function applyFilters() {{
      const selectedFilterList = Array.from(selectedFilters);
      const selectedCategoryList = Array.from(selectedCategories);
      const hasFilters = selectedFilterList.length > 0;
      const hasCategories = selectedCategoryList.length > 0;
      let totalVisible = 0;

      appCards.forEach((card) => {{
        const matchesFilters = !hasFilters || selectedFilterList.some((filter) => matchesFilter(card, filter));
        const matchesCategories = !hasCategories || selectedCategoryList.includes(card.dataset.categoryId);
        const isVisible = matchesFilters && matchesCategories;
        card.hidden = !isVisible;
        if (isVisible) totalVisible += 1;
      }});

      categorySections.forEach((section) => {{
        const visibleInSection = section.querySelectorAll(".app-card:not([hidden])").length;
        section.hidden = visibleInSection === 0;
        const counter = section.querySelector("[data-section-count]");
        if (counter) counter.textContent = pluralizeApps(visibleInSection);
      }});

      filterButtons.forEach((button) => {{
        button.setAttribute("aria-pressed", String(selectedFilters.has(button.dataset.filter)));
      }});
      categoryButtons.forEach((button) => {{
        button.setAttribute("aria-pressed", String(selectedCategories.has(button.dataset.categoryFilter)));
      }});

      visibleCount.textContent = String(totalVisible);
      const selectedCount = selectedFilterList.length + selectedCategoryList.length;
      activeFilter.textContent = selectedCount > 0 ? `${{selectedCount}} filter${{selectedCount === 1 ? "" : "s"}} selected` : "No filter selected";
      syncUrl();
    }}

    categoryButtons.forEach((button) => {{
      button.addEventListener("click", () => {{
        const category = button.dataset.categoryFilter;
        if (selectedCategories.has(category)) {{
          selectedCategories.delete(category);
        }} else {{
          selectedCategories.add(category);
        }}
        applyFilters();
      }});
    }});

    filterButtons.forEach((button) => {{
      button.addEventListener("click", () => {{
        const filter = button.dataset.filter;
        if (selectedFilters.has(filter)) {{
          selectedFilters.delete(filter);
        }} else {{
          selectedFilters.add(filter);
        }}
        applyFilters();
      }});
    }});

    const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const initialFilters = (hashParams.get("filters") || "")
      .split(",")
      .map((filter) => decodeURIComponent(filter))
      .filter((filter) => filters.includes(filter));
    const initialCategories = (hashParams.get("categories") || "")
      .split(",")
      .map((category) => decodeURIComponent(category))
      .filter((category) => categories.includes(category));
    initialFilters.forEach((filter) => selectedFilters.add(filter));
    initialCategories.forEach((category) => selectedCategories.add(category));
    applyFilters();
  </script>
</body>
</html>
"""


def main() -> None:
    categories = load_apps_yaml()
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "index.html").write_text(render(categories), encoding="utf-8")
    (OUT_DIR / ".nojekyll").write_text("", encoding="utf-8")


if __name__ == "__main__":
    main()
