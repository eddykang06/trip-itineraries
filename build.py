"""Build the trip itineraries site from Markdown.

    content/<trip>.md  -> <trip>/index.html, plus the list on index.html

Output goes to _site/. Run `python build.py` (needs `pip install markdown`).
"""

import datetime
import html
import re
import shutil
import urllib.parse
from pathlib import Path

import markdown

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
OUT = ROOT / "_site"

# Site settings. Set them as environment variables (the deploy reads GitHub repository
# variables) or in an untracked site.json, e.g. {"SITE_NAME": "Jane Doe", ...}.
SETTINGS = {
    "SITE_NAME": "Trips",           # name at the top of every page
    "SITE_HOME_URL": "",            # adds a "Home" link
    "SITE_STYLESHEET_URL": "",      # base stylesheet to match another site's look
    "SITE_FAVICON_URL": "",         # favicon image
}


def settings():
    import json, os
    local = ROOT / "site.json"
    found = json.loads(local.read_text(encoding="utf-8")) if local.exists() else {}
    return {k: os.environ.get(k) or found.get(k) or v for k, v in SETTINGS.items()}


def fill_site(page):
    """Fill the {{site_name}}, {{head}} and {{home_link}} placeholders."""
    s = settings()
    head = ""
    if s["SITE_FAVICON_URL"]:
        head += f'    <link rel="icon" href="{html.escape(s["SITE_FAVICON_URL"])}">\n'
    if s["SITE_STYLESHEET_URL"]:
        head += '    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        head += f'    <link rel="stylesheet" type="text/css" href="{html.escape(s["SITE_STYLESHEET_URL"])}">'
    home = f'<a href="{html.escape(s["SITE_HOME_URL"])}">Home</a> &nbsp;/&nbsp;\n        ' if s["SITE_HOME_URL"] else ""
    if "{{trips}}" in page and home:  # the index has nothing after the Home link
        home = home.split(" &nbsp;")[0]
    return (page.replace("{{site_name}}", html.escape(s["SITE_NAME"]))
            .replace("{{head}}", head.rstrip("\n"))
            .replace("{{home_link}}", home))


def fail(msg):
    raise SystemExit(f"Build failed: {msg}")


def read(path):
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def date_range(start, end):
    """Mar 5 – 12, 2027 / Mar 28 – Apr 3, 2027 / Dec 28, 2026 – Jan 4, 2027"""
    if start is None:
        return "Dates TBD"
    if start == end:
        return f"{start:%B} {start.day}, {start.year}"
    if start.year != end.year:
        return f"{start:%b} {start.day}, {start.year} – {end:%b} {end.day}, {end.year}"
    if start.month != end.month:
        return f"{start:%b} {start.day} – {end:%b} {end.day}, {end.year}"
    return f"{start:%B} {start.day} – {end.day}, {end.year}"


def parse_trip(path):
    text = read(path)
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    if not m:
        fail(f"{path.name} needs a header with a title (see content/_template.md)")
    meta = dict(line.split(":", 1) for line in m.group(1).split("\n") if ":" in line)
    meta = {k.strip().lower(): v.strip() for k, v in meta.items()}
    if "title" not in meta:
        fail(f"{path.name} needs 'title:' in its header")
    if "start" not in meta and "end" not in meta:  # dates TBD
        return {"slug": path.stem, "title": meta["title"], "start": None, "end": None, "body": m.group(2)}
    try:
        start = datetime.date.fromisoformat(meta.get("start", ""))
        end = datetime.date.fromisoformat(meta.get("end", ""))
    except ValueError:
        fail(f"{path.name}: start and end must both look like 2027-03-05 (or leave both out)")
    if end < start:
        fail(f"{path.name}: end is before start")
    return {"slug": path.stem, "title": meta["title"], "start": start, "end": end, "body": m.group(2)}


def inline(text):
    """Markdown for a single line or paragraph, without the surrounding <p>."""
    out = markdown.markdown(text.strip())
    return re.sub(r"^<p>(.*)</p>$", r"\1", out, flags=re.S)


ITEM = re.compile(r"^[-*] (.+)")
IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
MARKER = re.compile(r"^[-*+](\s+|(?=!\[))")  # "- " or "-![[...]]"
EMBED = re.compile(r"!\[\[([^\]|]+)(?:\|([^\]]*))?\]\]")


def embeds(text, source):
    """Obsidian image embeds ![[photo.png]] / ![[photo.png|alt]] -> ![alt](images/photo.png).
    The file is looked up by name anywhere under content/."""
    def resolve(m):
        name, alt = m.group(1).strip(), (m.group(2) or "").strip()
        found = sorted(CONTENT.rglob(Path(name).name))
        if not found:
            fail(f"{source}: can't find the image '{name}' in content/ (Obsidian should save pastes to content/images/)")
        path = found[0].relative_to(CONTENT).as_posix()
        alt = "" if alt.isdigit() or re.fullmatch(r"\d+x\d+", alt) else alt  # ![[x.png|300]] is a size
        return f"![{alt}]({urllib.parse.quote(path)})"
    return EMBED.sub(resolve, text)


GALLERY_HEIGHT = 260  # px; photos in a row are this tall when the page is wide enough


def aspect(src):
    """Width / height of an image under content/ (PNG, JPEG, GIF, WebP, SVG); 1 if unknown."""
    import struct
    path = CONTENT / urllib.parse.unquote(src)
    try:
        data = path.read_bytes()
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", data[16:24])
        elif data[:6] in (b"GIF87a", b"GIF89a"):
            w, h = struct.unpack("<HH", data[6:10])
        elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            if data[12:16] == b"VP8X":
                w = int.from_bytes(data[24:27], "little") + 1
                h = int.from_bytes(data[27:30], "little") + 1
            elif data[12:16] == b"VP8L":
                b = int.from_bytes(data[21:25], "little")
                w, h = (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
            else:
                w, h = struct.unpack("<HH", data[26:30])
        elif data[:2] == b"\xff\xd8":
            i = 2
            while i < len(data):
                marker, length = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
                if marker in (0xC0, 0xC1, 0xC2):
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    break
                i += 2 + length
        else:
            m = re.search(rb'viewBox="[\d.]+ [\d.]+ ([\d.]+) ([\d.]+)"', data[:2000])
            w, h = float(m[1]), float(m[2])
        return w / h if w and h else 1
    except Exception:
        return 1


def entry(title, lines):
    """One list item with indented lines under it -> a row with its title and description.
    One image: thumbnail on the left. Several: a row of photos under the description."""
    images, desc = [], []
    for line in lines:
        images += IMAGE.findall(line)
        rest = IMAGE.sub("", line).strip()
        if rest:
            desc.append(inline(rest))
    fallback = re.sub(r"<[^>]+>", "", inline(title))

    def img(alt, src, cls):
        cls = f' class="{cls}"' if cls else ""
        src = html.escape(src)
        return (f'<a class="photo-link" href="{src}" target="_blank">'
                f'<img{cls} src="{src}" alt="{html.escape(alt or fallback)}" loading="lazy"></a>')

    row = '<div class="entry">'
    if len(images) == 1:
        row += img(*images[0], "entry-img")
    row += f'<div class="entry-info"><span class="papertitle">{inline(title)}</span>'
    if desc:
        row += f'<div class="entry-desc">{"<br>".join(desc)}</div>'
    if len(images) > 1:
        # One line, no wrapping: each photo's share of the width follows its shape, so they
        # all come out the same height (GALLERY_HEIGHT, or less on narrow screens).
        ratios = [aspect(src) for _, src in images]
        width = sum(ratios) * GALLERY_HEIGHT + 8 * (len(images) - 1)
        row += f'<div class="entry-gallery" style="max-width: {width:.0f}px">'
        for (a, src), r in zip(images, ratios):
            row += img(a, src, "").replace('<a class="photo-link"', f'<a class="photo-link" style="flex: {r:.4f} 1 0"', 1)
        row += "</div>"
    return row + "</div></div>"


def entries(text):
    """Turn list items that have indented lines or sub-bullets under them into entry rows:
    each sub-bullet is a line of description, an image sub-bullet is the thumbnail.
    Plain one-line items stay normal bullets."""
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        m = ITEM.match(lines[i])
        if m:
            j = i + 1
            while j < len(lines) and lines[j][:1] in (" ", "\t") and lines[j].strip():
                j += 1
            extra = [MARKER.sub("", l.strip()) for l in lines[i + 1:j]]
            extra = [l for l in extra if l]
            if extra:
                out += ["", entry(m.group(1), extra), ""]
                i = j
                continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def render(text, source=""):
    body = markdown.markdown(entries(embeds(text, source)), extensions=["tables", "sane_lists"])
    # The trip title is the page's <h2>, so shift the itinerary's headings down one level.
    body = re.sub(r"<(/?)h([1-5])>", lambda m: f"<{m.group(1)}h{int(m.group(2)) + 1}>", body)
    # Image paths are written relative to content/; pages live one folder down.
    return re.sub(r'(<img[^>]*?\ssrc="|<a class="photo-link" href=")(?!https?:|/|data:)', r"\1../", body)


def build(drafts=False):
    """drafts=True also builds _files (used by preview.py, never by the deploy)."""
    trips = sorted(
        (parse_trip(p) for p in CONTENT.glob("*.md") if drafts or not p.name.startswith("_")),
        key=lambda t: (t["start"] is None, t["start"] or datetime.date.min),  # TBD last
    )

    template = fill_site(read(TEMPLATES / "trip.html"))
    for t in trips:
        out = OUT / t["slug"].lstrip("_")
        out.mkdir()
        page = (
            template.replace("{{title}}", html.escape(t["title"]))
            .replace("{{dates}}", date_range(t["start"], t["end"]))
            .replace("{{body}}", render(t["body"], t["slug"] + ".md"))
        )
        (out / "index.html").write_text(page, encoding="utf-8")

    if trips:
        listing = "".join(
            f'        <p>{date_range(t["start"], t["end"])} &nbsp;/&nbsp; '
            f'<a href="{t["slug"].lstrip("_")}/">{html.escape(t["title"])}</a></p>\n'
            for t in trips
        )
    else:
        listing = "        <p>No trips yet.</p>\n"
    (OUT / "index.html").write_text(fill_site(read(TEMPLATES / "index.html")).replace("{{trips}}", listing), encoding="utf-8")

    # images and folders saved next to trips (e.g. content/images/ -> images/)
    for f in CONTENT.iterdir():
        if f.is_dir():
            shutil.copytree(f, OUT / f.name)
        elif f.suffix != ".md":
            shutil.copy(f, OUT / f.name)


def build_site(drafts=False):
    for attempt in range(20):  # on Windows a file being served can be locked for a moment
        try:
            if OUT.exists():
                shutil.rmtree(OUT)
            break
        except PermissionError:
            if attempt == 19:
                raise
            import time
            time.sleep(0.25)
    OUT.mkdir()
    shutil.copy(ROOT / "trips.css", OUT)
    build(drafts)


if __name__ == "__main__":
    build_site()
    print(f"Built site in {OUT}")
