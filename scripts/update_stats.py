"""
update_stats.py

Regenerates the neofetch-style terminal block in README.md with:
  - uptime, calculated live from a fixed birthday (never hardcoded)
  - live GitHub stats: repos, stars, followers, contributed-to repos,
    total commits, and total lines of code

Run by .github/workflows/update.yml on a daily schedule and on every push.

Environment variables expected:
  GITHUB_USERNAME   - e.g. "naman616"
  GITHUB_TOKEN       - a token with `repo` + `read:user` scope
                        (a classic PAT stored as the PROFILE_TOKEN secret;
                        see SETUP.md for why the default GITHUB_TOKEN is not enough)
"""

import os
import sys
import requests
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(__file__))
from loc_counter import compute_total_loc

BIRTHDAY = date(2006, 10, 25)
README_PATH = os.path.join(os.path.dirname(__file__), "..", "README.md")
START_MARKER = "<!--START_SECTION:terminal-->"
END_MARKER = "<!--END_SECTION:terminal-->"

USERNAME = os.environ.get("GITHUB_USERNAME", "naman616")
TOKEN = os.environ.get("GITHUB_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
}


def calc_uptime(birthday: date) -> str:
    """Years / months / days since birthday, computed fresh every run."""
    today = date.today()
    years = today.year - birthday.year
    months = today.month - birthday.month
    days = today.day - birthday.day

    if days < 0:
        months -= 1
        # days in the previous month
        prev_month = today.month - 1 or 12
        prev_year = today.year if today.month > 1 else today.year - 1
        from calendar import monthrange
        days += monthrange(prev_year, prev_month)[1]

    if months < 0:
        years -= 1
        months += 12

    parts = []
    if years:
        parts.append(f"{years} year{'s' if years != 1 else ''}")
    if months:
        parts.append(f"{months} month{'s' if months != 1 else ''}")
    parts.append(f"{days} day{'s' if days != 1 else ''}")
    return ", ".join(parts)


def graphql(query, variables=None):
    resp = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables or {}},
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def get_basic_profile():
    r = requests.get(f"https://api.github.com/users/{USERNAME}", headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def get_owned_repos():
    """All non-fork public repos owned by the user (for stars + clone list)."""
    repos = []
    page = 1
    while True:
        r = requests.get(
            f"https://api.github.com/users/{USERNAME}/repos",
            params={"per_page": 100, "page": page, "type": "owner"},
            headers=HEADERS,
            timeout=30,
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos


def get_contributed_and_commits():
    """
    Total commit contributions and distinct repos contributed to, summed across
    every year since account creation (contributionsCollection is capped at 1 year
    per query, so we loop year by year).
    """
    profile = graphql(
        """
        query($login: String!) {
          user(login: $login) { createdAt }
        }
        """,
        {"login": USERNAME},
    )
    created_at = datetime.strptime(profile["user"]["createdAt"][:10], "%Y-%m-%d")
    start_year = created_at.year
    current_year = datetime.utcnow().year

    total_commits = 0
    contributed_repo_names = set()

    for year in range(start_year, current_year + 1):
        frm = f"{year}-01-01T00:00:00Z"
        to = f"{year}-12-31T23:59:59Z"
        data = graphql(
            """
            query($login: String!, $from: DateTime!, $to: DateTime!) {
              user(login: $login) {
                contributionsCollection(from: $from, to: $to) {
                  totalCommitContributions
                  totalRepositoriesWithContributedCommits
                  commitContributionsByRepository(maxRepositories: 100) {
                    repository { nameWithOwner }
                  }
                }
              }
            }
            """,
            {"login": USERNAME, "from": frm, "to": to},
        )
        cc = data["user"]["contributionsCollection"]
        total_commits += cc["totalCommitContributions"]
        for item in cc["commitContributionsByRepository"]:
            contributed_repo_names.add(item["repository"]["nameWithOwner"])

    return len(contributed_repo_names), total_commits


def format_int(n: int) -> str:
    return f"{n:,}"


def build_info_lines(stats: dict) -> list:
    def line(label, value):
        dots = "." * max(2, 40 - len(label) - len(value))
        return f"{label}: {dots} {value}"

    return [
        "naman@lodha",
        "-----------",
        line("OS", "macOS, Linux, Windows, iOS, Android"),
        line("Uptime", stats["uptime"]),
        line("Host", "Naman Lodha"),
        line("Kernel", "CAM (Computer Aided Manufacturing) Operator"),
        line("IDE", "IntelliJ IDEA, VSCode, Antigravity"),
        "",
        line("Languages.Programming", "C, Python, JavaScript, Java"),
        line("Languages.Computer", "HTML, CSS, JSON, LaTeX, YAML"),
        line("Languages.Real", "English, Hindi"),
        "",
        "- Contact -",
        line("Email", "namanlodha616@gmail.com"),
        line("GitHub", "naman616"),
        line("LinkedIn", "Naman Lodha"),
        line("LeetCode", "namanld"),
        "",
        "- GitHub Stats -",
        line("Repos", format_int(stats["repos"])),
        line("Contributed", format_int(stats["contributed"])),
        line("Followers", format_int(stats["followers"])),
        line("Stars", format_int(stats["stars"])),
        line("Commits", format_int(stats["commits"])),
        line("Lines of Code", format_int(stats["loc"])),
    ]


def build_terminal_block(stats: dict) -> str:
    return "\n".join(build_info_lines(stats))


def update_readme(block: str):
    with open(README_PATH, "r") as f:
        content = f.read()

    start = content.index(START_MARKER) + len(START_MARKER)
    end = content.index(END_MARKER)
    new_content = content[:start] + "\n" + block + "\n" + content[end:]

    with open(README_PATH, "w") as f:
        f.write(new_content)


def main():
    profile = get_basic_profile()
    owned_repos = get_owned_repos()

    stars = sum(r.get("stargazers_count", 0) for r in owned_repos)
    contributed, commits = get_contributed_and_commits()

    author_emails = [
        f"{USERNAME}@users.noreply.github.com",
        "namanlodha616@gmail.com",
    ]
    clone_targets = [
        {"full_name": r["full_name"], "clone_url": r["clone_url"]}
        for r in owned_repos
        if not r.get("fork")
    ]
    net_loc, _add, _del = compute_total_loc(clone_targets, author_emails)

    stats = {
        "uptime": calc_uptime(BIRTHDAY),
        "repos": profile.get("public_repos", len(owned_repos)),
        "stars": stars,
        "contributed": contributed,
        "followers": profile.get("followers", 0),
        "commits": commits,
        "loc": net_loc,
    }

    block = build_terminal_block(stats)
    update_readme(block)
    print("README.md updated successfully.")


if __name__ == "__main__":
    main()
