"""
loc_counter.py

Clones every repo owned by (or contributed to by) a GitHub user and sums the
net lines of code (additions - deletions) authored by that user across the
full commit history.

To keep this fast on every run, results are cached per-repo in cache/loc_cache.json.
On each run, only commits newer than the last-seen SHA for a given repo are
processed, so the full history is only ever walked once per repo.
"""

import json
import os
import subprocess
import tempfile
import shutil

CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "cache", "loc_cache.json")


def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def run(cmd, cwd=None):
    return subprocess.run(
        cmd, cwd=cwd, shell=True, capture_output=True, text=True
    ).stdout


def scan_repo(repo_full_name, clone_url, author_emails, cache):
    """Clone a single repo (or reuse) and accumulate net line changes by author."""
    entry = cache.get(repo_full_name, {"last_sha": None, "additions": 0, "deletions": 0})

    tmp_dir = tempfile.mkdtemp(prefix="loc_")
    try:
        clone_result = subprocess.run(
            ["git", "clone", "--quiet", clone_url, tmp_dir],
            capture_output=True, text=True, timeout=300,
        )
        if clone_result.returncode != 0:
            # private / inaccessible / renamed repo -- skip gracefully
            return entry

        head_sha = run("git rev-parse HEAD", cwd=tmp_dir).strip()
        if not head_sha:
            return entry

        if entry["last_sha"] == head_sha:
            # nothing new since last scan
            return entry

        rev_range = f"{entry['last_sha']}..HEAD" if entry["last_sha"] else "HEAD"

        author_filter = " ".join(f'--author="{e}"' for e in author_emails)
        log = run(
            f'git log {rev_range} {author_filter} --pretty=tformat: --numstat',
            cwd=tmp_dir,
        )

        additions = deletions = 0
        for line in log.splitlines():
            parts = line.split("\t")
            if len(parts) == 3:
                add, rem, _path = parts
                if add.isdigit():
                    additions += int(add)
                if rem.isdigit():
                    deletions += int(rem)

        entry["additions"] += additions
        entry["deletions"] += deletions
        entry["last_sha"] = head_sha
        return entry
    except Exception:
        return entry
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def compute_total_loc(repos, author_emails):
    """
    repos: list of dicts with keys 'full_name' and 'clone_url'
    author_emails: list of git commit emails / noreply emails belonging to the user
    Returns (net_lines, additions, deletions) and updates the on-disk cache.
    """
    cache = load_cache()
    total_add = total_del = 0

    for repo in repos:
        result = scan_repo(repo["full_name"], repo["clone_url"], author_emails, cache)
        cache[repo["full_name"]] = result
        total_add += result["additions"]
        total_del += result["deletions"]

    save_cache(cache)
    net = total_add - total_del
    return net, total_add, total_del
