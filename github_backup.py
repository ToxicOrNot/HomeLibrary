import base64
import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_INTERVAL_SECONDS = 24 * 60 * 60
LAST_STATUS = "GitHub backup has not run yet."


def backup_if_due(data_file: Path, force: bool = False) -> bool:
    token = get_config("GITHUB_TOKEN")
    repo = get_config("GITHUB_REPOSITORY") or get_config("GITHUB_REPO")
    if not token:
        set_status("GitHub backup skipped: GITHUB_TOKEN is not configured.")
        return False
    if not repo:
        set_status("GitHub backup skipped: GITHUB_REPOSITORY is not configured.")
        return False
    if not data_file.exists():
        set_status(f"GitHub backup skipped: data file does not exist: {data_file}")
        return False

    interval = int(get_config("GITHUB_BACKUP_INTERVAL_SECONDS", str(DEFAULT_INTERVAL_SECONDS)))
    state_file = Path(
        get_config(
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
        set_status("GitHub backup skipped: interval has not elapsed.")
        return False

    branch = get_config("GITHUB_BRANCH", "main")
    backup_path = get_config("GITHUB_BACKUP_PATH", default_backup_path(data_file))
    content = data_file.read_bytes()
    sha = get_remote_sha(token, repo, backup_path, branch)
    upload_backup(token, repo, backup_path, branch, content, sha)

    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(str(now), encoding="utf-8")
    set_status(f"GitHub backup completed: {repo}/{backup_path}.")
    return True


def get_config(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value:
        return str(value).strip()

    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name]).strip()

        github_secrets = st.secrets.get("github", {})
        if name in github_secrets:
            return str(github_secrets[name]).strip()
    except Exception:
        pass

    return default.strip()


def set_status(message: str) -> None:
    global LAST_STATUS
    LAST_STATUS = message


def get_last_backup_status() -> str:
    return LAST_STATUS


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


def restore_from_github(data_file: Path) -> str:
    token = get_config("GITHUB_TOKEN")
    repo = get_config("GITHUB_REPOSITORY") or get_config("GITHUB_REPO")
    if not token:
        set_status("GitHub restore skipped: GITHUB_TOKEN is not configured.")
        return "skipped"
    if not repo:
        set_status("GitHub restore skipped: GITHUB_REPOSITORY is not configured.")
        return "skipped"

    branch = get_config("GITHUB_BRANCH", "main")
    backup_path = get_config("GITHUB_BACKUP_PATH", default_backup_path(data_file))
    url = f"https://api.github.com/repos/{repo}/contents/{backup_path}?ref={branch}"

    try:
        response = github_request(token, url)
    except HTTPError as error:
        if error.code == 404:
            set_status(f"GitHub restore skipped: remote file not found: {repo}/{backup_path}.")
            return "missing"
        raise

    encoded = str(response.get("content", "")).replace("\n", "")
    if not encoded:
        set_status(f"GitHub restore skipped: remote file is empty: {repo}/{backup_path}.")
        return "missing"

    content = base64.b64decode(encoded)
    json.loads(content.decode("utf-8"))

    data_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file = data_file.with_suffix(data_file.suffix + ".tmp")
    temp_file.write_bytes(content)
    temp_file.replace(data_file)
    set_status(f"GitHub restore completed: {repo}/{backup_path}.")
    return "restored"


def safe_backup_if_due(data_file: Path, force: bool = False) -> bool:
    try:
        return backup_if_due(data_file, force=force)
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        set_status(f"GitHub backup failed: HTTP {error.code}. {details[:300]}")
        return False
    except (OSError, URLError, TimeoutError, json.JSONDecodeError) as error:
        set_status(f"GitHub backup failed: {error}")
        return False


def safe_restore_from_github(data_file: Path) -> str:
    try:
        return restore_from_github(data_file)
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        set_status(f"GitHub restore failed: HTTP {error.code}. {details[:300]}")
        return "failed"
    except (OSError, URLError, TimeoutError, json.JSONDecodeError, ValueError) as error:
        set_status(f"GitHub restore failed: {error}")
        return "failed"
