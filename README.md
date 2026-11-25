# trip-itineraries

A small static site for trip itineraries. Each trip is one Markdown file; `build.py` turns them into pages and GitHub Actions deploys them to GitHub Pages. It can borrow the stylesheet of an existing site so the pages match it, and the folder works as an [Obsidian](https://obsidian.md/) vault.

## Writing a trip

Each trip is one Markdown file in `content/`. Start from `content/_template.md`, which shows every element.

- The file name becomes the URL: `content/japan-2027.md` → `<site>/japan-2027/`.
- The header (Obsidian "properties") has `title`, and optionally `start` and `end` as `2027-03-05`. Without dates the page says "Dates TBD". Trips are listed by start date.
- `##` headings for days or areas, `###` for parts of a day or sub-sections. Tables, lists, links and `>` note boxes work.
- Files whose names start with `_` are drafts: they show up in the local preview but are not published.

### Places with descriptions and images

A plain bullet stays a bullet. Sub-bullets under a bullet turn it into a row with a thumbnail, a bold title and description lines:

```markdown
- Saltie Girl · [site](https://www.saltiegirl.com/)
	- Tiny seafood bar.
	- Get the lobster roll.
	- ![[saltie-girl.jpg]]
- Prudential Center
```

Each sub-bullet is one line of description; an image sub-bullet becomes the thumbnail. Images can be Obsidian embeds (`![[name.jpg]]`, looked up by file name anywhere in `content/`) or Markdown (`![alt](images/name.jpg)`, relative to `content/`). An image on its own line outside a list is shown full width.

## Using it with Obsidian

Open the repo folder as a vault. Suggested settings (Settings > Files and links): default location for new notes `content`, attachment folder `content/images`. With the [Obsidian Git](https://github.com/Vinzent03/obsidian-git) plugin set to commit and push on an interval, saving a note republishes the site.

## Site settings

Set these as GitHub repository variables (Settings > Secrets and variables > Actions > Variables) for the deploy, and in an untracked `site.json` for local builds. All are optional.

| Setting | What it does |
|---|---|
| `SITE_NAME` | Name at the top of every page (default "Trips") |
| `SITE_HOME_URL` | Adds a "Home" link |
| `SITE_STYLESHEET_URL` | Base stylesheet, for example your main site's, so the pages match it |
| `SITE_FAVICON_URL` | Favicon image |

```json
{
  "SITE_NAME": "Jane Doe",
  "SITE_HOME_URL": "https://example.github.io/",
  "SITE_STYLESHEET_URL": "https://example.github.io/stylesheet.css"
}
```

The page layout and `trips.css` are designed for stylesheets based on [Jon Barron's website template](https://github.com/jonbarron/jonbarron.github.io).

## Building and previewing

```
pip install markdown
python preview.py    # http://localhost:8000, includes drafts, reloads on save
python build.py      # writes the published site to _site/
```

## Deploying

In the repo's Settings > Pages, set Source to "GitHub Actions". Every push to `main` builds and deploys the site.

GitHub Pages sites are public. Pages are marked `noindex` so search engines skip them, but anyone with the link can read them, and drafts are visible in a public repo. Leave out addresses, booking numbers and anything else you wouldn't post.

## Credit

Page layout from [Jon Barron's website template](https://github.com/jonbarron/jonbarron.github.io).
