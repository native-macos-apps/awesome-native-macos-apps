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
    # If no icon, return default SVG
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
    category_menu_items = "\n".join(
        f'<a class="menu-item" href="#{html.escape(category["id"])}" data-category-link="{html.escape(category["id"])}">'
        f'<span class="menu-name">{html.escape(category["name"])}</span>'
        f'<span class="menu-count" data-menu-count="{html.escape(category["id"])}">{len(category.get("apps", []))}</span>'
        f'</a>'
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
                    <img class="app-icon" src="{html.escape(icon_url)}" alt="{html.escape(app['name'])} icon" width="40" height="40" loading="lazy" onerror="this.onerror=null; this.src=&quot;data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%230071e3' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='3' y='3' width='18' height='18' rx='2' ry='2'%3E%3C/rect%3E%3C/svg%3E&quot;;" />
                    <div class="app-title-wrapper">
                      <div class="app-title">
                        <a href="{html.escape(app['url'])}" rel="noopener noreferrer" target="_blank">{html.escape(app['name'])}</a>
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
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #f8f9fa;
      --text: #1d1d1f;
      --muted: #86868b;
      --line: #e2e2e7;
      --card: #ffffff;
      --accent: #0071e3;
      --accent-light: rgba(0, 113, 227, 0.08);
      --tag: #f5f5f7;
      --tag-text: #1d1d1f;
      --shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
      --sidebar-bg: #ffffff;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #000000;
        --text: #f5f5f7;
        --muted: #86868b;
        --line: #2c2c2e;
        --card: #1c1c1e;
        --accent: #2997ff;
        --accent-light: rgba(41, 151, 255, 0.15);
        --tag: #2c2c2e;
        --tag-text: #f5f5f7;
        --shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        --sidebar-bg: #161617;
      }}
    }}
    * {{ box-sizing: border-box; }}
    html {{
      scroll-behavior: smooth;
      scroll-padding-top: 24px;
    }}
    body {{
      margin: 0;
      font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 320px 1fr;
      min-height: 100vh;
      max-width: 1440px;
      margin: 0 auto;
    }}
    .sidebar {{
      position: sticky;
      top: 0;
      height: 100vh;
      overflow-y: auto;
      border-right: 1px solid var(--line);
      padding: 48px 32px;
      display: flex;
      flex-direction: column;
      gap: 32px;
      background: var(--sidebar-bg);
      scrollbar-width: thin;
    }}
    .sidebar::-webkit-scrollbar {{
      width: 4px;
    }}
    .sidebar::-webkit-scrollbar-thumb {{
      background: var(--line);
      border-radius: 4px;
    }}
    .content {{
      padding: 48px 64px;
      max-width: 1120px;
      overflow-y: auto;
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: 1.8rem;
      font-weight: 700;
      line-height: 1.2;
      letter-spacing: -0.02em;
    }}
    .sidebar p {{
      margin: 0;
      color: var(--muted);
      font-size: 0.9rem;
      line-height: 1.5;
    }}
    .stats {{
      display: flex;
      gap: 20px;
      color: var(--muted);
      font-size: 0.85rem;
      border-bottom: 1px solid var(--line);
      padding-bottom: 24px;
    }}
    .stats span {{
      display: flex;
      flex-direction: column;
    }}
    .stats strong {{
      color: var(--text);
      font-size: 1.2rem;
      font-weight: 600;
    }}
    .filter-section {{
      display: flex;
      flex-direction: column;
      gap: 12px;
      border-bottom: 1px solid var(--line);
      padding-bottom: 24px;
    }}
    .filter-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .filter-header strong {{
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted);
    }}
    .filter-header span {{
      font-size: 0.8rem;
      color: var(--muted);
    }}
    .filter-buttons {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .filter-button {{
      background: transparent;
      border: 1px solid var(--line);
      border-radius: 8px;
      color: var(--text);
      cursor: pointer;
      display: inline-flex;
      font: inherit;
      font-size: 0.82rem;
      font-weight: 500;
      padding: 6px 12px;
      transition: all 0.2s ease;
    }}
    .filter-button:hover {{
      border-color: var(--text);
    }}
    .filter-button[aria-pressed="true"] {{
      background: var(--text);
      border-color: var(--text);
      color: var(--bg);
    }}
    .category-menu {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .menu-header {{
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted);
      margin-bottom: 8px;
      font-weight: 600;
    }}
    .menu-item {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      color: var(--muted);
      text-decoration: none;
      border-radius: 8px;
      font-size: 0.9rem;
      font-weight: 500;
      transition: all 0.2s ease;
    }}
    .menu-item:hover {{
      background: var(--tag);
      color: var(--text);
    }}
    .menu-item.active {{
      background: var(--accent-light);
      color: var(--accent);
      font-weight: 600;
    }}
    .menu-count {{
      font-size: 0.75rem;
      background: var(--tag);
      padding: 2px 6px;
      border-radius: 6px;
      color: var(--muted);
      font-weight: 600;
      transition: all 0.2s ease;
    }}
    .menu-item.active .menu-count {{
      background: var(--accent);
      color: #ffffff;
    }}
    section {{
      padding: 32px 0 48px;
      border-bottom: 1px solid var(--line);
    }}
    section:last-of-type {{
      border-bottom: none;
    }}
    .section-heading {{
      align-items: baseline;
      display: flex;
      gap: 12px;
      justify-content: space-between;
      margin-bottom: 8px;
    }}
    h2 {{
      font-size: 1.6rem;
      font-weight: 700;
      margin: 0;
      letter-spacing: -0.01em;
    }}
    .section-heading span {{
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .section-description {{
      color: var(--muted);
      margin: 0 0 24px 0;
      font-size: 0.95rem;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 16px;
    }}
    .app-card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      min-height: 200px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      box-shadow: var(--shadow);
      transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }}
    .app-card:hover {{
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
      border-color: var(--accent);
    }}
    @media (prefers-color-scheme: dark) {{
      .app-card:hover {{
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
      }}
    }}
    .app-header {{
      display: flex;
      align-items: center;
      gap: 14px;
      margin-bottom: 14px;
    }}
    .app-icon {{
      border-radius: 10px;
      border: 1px solid var(--line);
      background: var(--card);
      height: 40px;
      width: 40px;
      object-fit: contain;
      padding: 4px;
      flex-shrink: 0;
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
      font-size: 1.1rem;
      font-weight: 600;
      text-decoration: none;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .app-title a:hover {{ color: var(--accent); }}
    .price {{
      color: var(--accent);
      text-transform: capitalize;
      font-size: 0.75rem;
      font-weight: 600;
      background: var(--accent-light);
      padding: 2px 8px;
      border-radius: 6px;
      border: none;
    }}
    .app-card p {{
      color: var(--muted);
      margin: 0 0 16px 0;
      font-size: 0.9rem;
      line-height: 1.45;
      flex-grow: 1;
    }}
    .meta-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .meta {{
      font-size: 0.75rem;
      font-weight: 500;
      background: var(--tag);
      color: var(--muted);
      border: none;
      border-radius: 6px;
      padding: 2px 8px;
    }}
    .tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 12px;
    }}
    .tag {{
      background: var(--tag);
      color: var(--tag-text);
      border: none;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 500;
      padding: 2px 8px;
    }}
    [hidden] {{ display: none !important; }}
    footer {{
      color: var(--muted);
      padding: 48px 0;
      text-align: center;
      font-size: 0.85rem;
      border-top: 1px solid var(--line);
      margin-top: 40px;
    }}
    @media (max-width: 1024px) {{
      .layout {{
        grid-template-columns: 1fr;
      }}
      .sidebar {{
        position: static;
        height: auto;
        border-right: none;
        border-bottom: 1px solid var(--line);
        padding: 32px 24px;
        background: var(--sidebar-bg);
      }}
      .content {{
        padding: 32px 24px;
      }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <div class="sidebar-header">
        <h1>Awesome Native macOS Apps</h1>
        <p>A curated collection of macOS apps prioritizing native experience, system integration, and performance.</p>
      </div>
      <div class="stats">
        <span><strong id="visible-count">{app_count}</strong> apps</span>
        <span><strong>{len(categories)}</strong> categories</span>
      </div>
      <div class="filter-section">
        <div class="filter-header">
          <strong>Filters</strong>
          <span id="active-filter">No filter selected</span>
        </div>
        <div class="filter-buttons">
          {filters}
        </div>
      </div>
      <nav class="category-menu" aria-label="Categories">
        <div class="menu-header">Categories</div>
        {category_menu_items}
      </nav>
    </aside>
    <main class="content">
      {"".join(sections)}
      <footer>Built with GitHub Actions and GitHub Pages.</footer>
    </main>
  </div>
  <script>
    const appCards = Array.from(document.querySelectorAll(".app-card"));
    const categorySections = Array.from(document.querySelectorAll("[data-category]"));
    const menuItems = Array.from(document.querySelectorAll(".menu-item"));
    const filterButtons = Array.from(document.querySelectorAll("[data-filter]"));
    const visibleCount = document.querySelector("#visible-count");
    const activeFilter = document.querySelector("#active-filter");
    const filters = {json.dumps([value for value, _label in filter_options])};
    const categories = {json.dumps([category["id"] for category in categories])};
    const selectedFilters = new Set();

    function pluralizeApps(count) {{
      return count === 1 ? "1 app" : `${{count}} apps`;
    }}

    function syncUrl() {{
      const selectedFilterList = Array.from(selectedFilters);
      const params = new URLSearchParams();
      if (selectedFilterList.length > 0) {{
        params.set("filters", selectedFilterList.map((filter) => encodeURIComponent(filter)).join(","));
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
      const hasFilters = selectedFilterList.length > 0;
      let totalVisible = 0;

      appCards.forEach((card) => {{
        const matchesFilters = !hasFilters || selectedFilterList.some((filter) => matchesFilter(card, filter));
        card.hidden = !matchesFilters;
        if (matchesFilters) totalVisible += 1;
      }});

      categorySections.forEach((section) => {{
        const visibleInSection = section.querySelectorAll(".app-card:not([hidden])").length;
        const isHidden = visibleInSection === 0;
        section.hidden = isHidden;
        
        // Hide/show sidebar category menu link
        const menuLink = document.querySelector(`.menu-item[data-category-link="${{section.id}}"]`);
        if (menuLink) {{
          menuLink.hidden = isHidden;
        }}

        const counter = section.querySelector("[data-section-count]");
        if (counter) counter.textContent = pluralizeApps(visibleInSection);

        const menuCount = document.querySelector(`[data-menu-count="${{section.id}}"]`);
        if (menuCount) menuCount.textContent = String(visibleInSection);
      }});

      filterButtons.forEach((button) => {{
        button.setAttribute("aria-pressed", String(selectedFilters.has(button.dataset.filter)));
      }});

      visibleCount.textContent = String(totalVisible);
      const selectedCount = selectedFilterList.length;
      activeFilter.textContent = selectedCount > 0 ? `${{selectedCount}} filter${{selectedCount === 1 ? "" : "s"}} selected` : "No filter selected";
      syncUrl();
    }}

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

    // Scroll Spy
    const observerOptions = {{
      root: null,
      rootMargin: '-10% 0px -80% 0px',
      threshold: 0
    }};

    const observer = new IntersectionObserver((entries) => {{
      entries.forEach(entry => {{
        if (entry.isIntersecting && !entry.target.hidden) {{
          const id = entry.target.getAttribute('id');
          menuItems.forEach(item => {{
            item.classList.toggle('active', item.dataset.categoryLink === id);
          }});
        }}
      }});
    }}, observerOptions);

    categorySections.forEach(section => {{
      observer.observe(section);
    }});

    // Handle hash parameters on load
    const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const initialFilters = (hashParams.get("filters") || "")
      .split(",")
      .map((filter) => decodeURIComponent(filter))
      .filter((filter) => filters.includes(filter));
    initialFilters.forEach((filter) => selectedFilters.add(filter));
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
