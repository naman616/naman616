# Setup instructions

## 1. Repo location

Create (or reuse) a repository with the **exact same name as your username**:
`https://github.com/naman616/naman616`
GitHub automatically renders that repo's `README.md` on your profile page.

Push everything in this folder to the root of that repo:

```
naman616/
├── README.md
├── assets/
│   ├── profile_source.jpg    (your original selfie -- kept for reference/regeneration)
│   ├── ascii_art.txt         (the ASCII portrait, plain text -- source of truth)
│   ├── ascii_art_dark.svg    (generated -- shown to dark-mode viewers)
│   └── ascii_art_light.svg   (generated -- shown to light-mode viewers)
├── cache/
│   └── loc_cache.json
├── .github/
│   └── workflows/
│       └── update.yml
└── scripts/
    ├── update_stats.py
    ├── loc_counter.py
    ├── generate_ascii.py
    ├── build_ascii_svg.py
    └── requirements.txt
```

## 2. Create a Personal Access Token (required)

The default `GITHUB_TOKEN` that GitHub Actions provides automatically **cannot**:
- read your full contribution history (`contributionsCollection` in the GraphQL API), or
- clone your other repos to count lines of code.

So you need one Personal Access Token (PAT):

1. Go to **GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)**.
2. Generate a new token with these scopes:
   - `repo` (full control of private repos — needed to clone/read all your repos)
   - `read:user` (needed for contribution + follower data)
3. Copy the token.
4. In the `naman616/naman616` repo, go to **Settings → Secrets and variables → Actions → New repository secret**.
5. Name it `PROFILE_TOKEN` and paste the token value.

## 3. Push

```bash
git init
git add .
git commit -m "Initial terminal profile"
git branch -M main
git remote add origin https://github.com/naman616/naman616.git
git push -u origin main
```

## 4. What happens next

- The workflow in `.github/workflows/update.yml` runs automatically:
  - once a day at midnight UTC (keeps uptime and stats fresh even with no activity)
  - on every push to `main`
  - or manually, any time, from the **Actions** tab → "Update profile terminal" → **Run workflow**
- It recalculates your uptime from your birthday, pulls live stats from the GitHub API,
  scans your repos for lines of code (caching progress in `cache/loc_cache.json` so it gets
  faster over time), rewrites the terminal block in `README.md` between the
  `<!--START_SECTION:terminal--> / <!--END_SECTION:terminal-->` markers, and commits the result.
- Nothing in the stats block is ever hardcoded — deleting `cache/loc_cache.json` just makes the
  next run re-scan full history instead of resuming from the cache.

## 5. Updating personal details later

Everything outside the `<!--START_SECTION-->` / `<!--END_SECTION-->` markers (name, contact info,
languages, IDEs, OS list) is plain static text at the top of `scripts/update_stats.py`'s
`build_terminal_block()` function and in the initial `README.md`. Edit it there and the next
workflow run will keep it in place.

## 6. How the ASCII portrait is displayed

The README doesn't inline raw ASCII text — GitHub can't guarantee monospace column
alignment across every viewer's font, and a huge block of loose text would fight with the
terminal card next to it. Instead:

- `assets/ascii_art.txt` is the source of truth (currently your own custom ASCII art).
- `scripts/build_ascii_svg.py` renders it into **two** SVGs: `ascii_art_dark.svg`
  (dark terminal background, light text) and `ascii_art_light.svg` (light background, dark
  text). Every row is stretched to an identical `textLength`, so columns stay pixel-perfect
  regardless of font substitution.
- `README.md` uses a `<picture>` element with `prefers-color-scheme` media queries to pick the
  matching one automatically:

  ```html
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/ascii_art_dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/ascii_art_light.svg">
    <img src="assets/ascii_art_dark.svg" height="440" alt="...">
  </picture>
  ```

  This is GitHub's own recommended technique for theme-adaptive images (more reliable than a
  single SVG with an internal media query, since some renderers strip `<style>` media queries
  out of images fetched via `<img src>`). The `<img>` fallback is the dark version, since most
  visitors browse GitHub in dark mode.
- The `height="440"` on the `<img>` is a vector scale-down (no blurring) that roughly matches
  the height of the terminal-info text column on the right, so the two sides line up as one
  balanced card. If your info column grows or shrinks a lot, adjust that number — a good rule
  of thumb is roughly 17-18px per line in the right-hand column.

To update the ASCII art itself, edit/replace `assets/ascii_art.txt` and re-run:

```bash
python scripts/build_ascii_svg.py
git add assets/ascii_art.txt assets/ascii_art_dark.svg assets/ascii_art_light.svg
git commit -m "Update ASCII portrait"
git push
```

The workflow also rebuilds both SVGs automatically on every run, so pushing an updated
`ascii_art.txt` alone is enough — you don't have to run the script locally.

### Regenerating ASCII from a photo instead

If you'd rather regenerate the ASCII art from a selfie again (instead of hand-editing
`ascii_art.txt`), `scripts/generate_ascii.py` is still here for that:
it detects your face in `assets/profile_source.jpg`, crops tightly to head + shoulders,
converts to grayscale, boosts contrast, and maps brightness to the character ramp
`" .:-=+*#%@"` (no Unicode blocks, no emoji). It is **not** run automatically by the
workflow (so it won't overwrite your custom art) — run it manually when you want it:

```bash
cp your-new-selfie.jpg assets/profile_source.jpg
python scripts/generate_ascii.py
python scripts/build_ascii_svg.py
git add assets/profile_source.jpg assets/ascii_art.txt assets/ascii_art_dark.svg assets/ascii_art_light.svg
git commit -m "Regenerate ASCII portrait from new photo"
git push
```

The knobs for that pipeline (`ASCII_WIDTH` / `ASCII_HEIGHT`, the `CHARSET` density ramp, and
contrast/sharpness factors) are all in `scripts/generate_ascii.py`.

## 7. First-run note on Lines of Code

The very first workflow run clones every one of your public repos and walks their full commit
history, so it may take a few minutes on a large account. Every run after that only processes
commits made since the last run, so it stays fast.
