import base64
import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_INTERVAL_SECONDS = 24 * 60 * 60


def backup_if_due(data_file: Path, force: bool = False) -> bool:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", os.environ.get("GITHUB_REPO", "")).strip()
    if not token or not repo or not data_file.exists():
        return False

    interval = int(os.environ.get("GITHUB_BACKUP_INTERVAL_SECONDS", DEFAULT_INTERVAL_SECONDS))
    state_file = Path(
        os.environ.get(
            "GITHUB_BACKUP_STATE_FILE",
            data_file.with_name(".last_github_backup").as_posix(),
        )
    )
    now = time.time()

    try:
        last_backup = float(state_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        last_backup = 0

    if not force and now - last_backup < interval:
        return False

    branch = os.environ.get("GITHUB_BRANCH", "main").strip()
    backup_path = os.environ.get("GITHUB_BACKUP_PATH", default_backup_path(data_file)).strip()
    content = data_file.read_bytes()
    sha = get_remote_sha(token, repo, backup_path, branch)
    upload_backup(token, repo, backup_path, branch, content, sha)

    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(str(now), encoding="utf-8")
    return True


def github_request(token: str, url: str, method: str = "GET", payload: dict | None = None):
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "home-library-backup",
        },
    )
    with urlopen(request, timeout=20) as response:
        body = response.read().decode("utf-8")
        return json.loads(body) if body else {}


def default_backup_path(data_file: Path) -> str:
    try:
        return data_file.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return data_file.name


def get_remote_sha(token: str, repo: str, path: str, branch: str) -> str | None:
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
    try:
        response = github_request(token, url)
    except HTTPError as error:
        if error.code == 404:
            return None
        raise
    return response.get("sha")


def upload_backup(
    token: str,
    repo: str,
    path: str,
    branch: str,
    content: bytes,
    sha: str | None,
) -> None:
    payload = {
        "message": "Backup library data",
        "content": base64.b64encode(content).decode("ascii"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    github_request(token, url, method="PUT", payload=payload)


def safe_backup_if_due(data_file: Path, force: bool = False) -> bool:
    try:
        return backup_if_due(data_file, force=force)
    except (OSError, HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return False
