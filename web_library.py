# -*- coding: utf-8 -*-
import json
import os
import socket
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


DATA_FILE = Path(os.environ.get("DATA_FILE", Path(__file__).with_name("library_data.json")))
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8000"))


EMPTY_DATA = {"owned": [], "wishlist": []}
VALID_LISTS = {"owned", "wishlist"}


INDEX_HTML = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Домашняя библиотека</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f3ef;
      --panel: #ffffff;
      --text: #1f2933;
      --muted: #64748b;
      --line: #d8dee7;
      --primary: #2457a6;
      --primary-dark: #183f7a;
      --danger: #b42318;
      --ok: #1f7a4c;
      --shadow: 0 10px 28px rgba(31, 41, 51, 0.08);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .page {
      width: min(1160px, 100%);
      margin: 0 auto;
      padding: 20px;
    }

    header {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 16px;
    }

    h1 {
      margin: 0;
      font-size: 30px;
      line-height: 1.1;
    }

    .status {
      color: var(--muted);
      font-size: 14px;
      text-align: right;
    }

    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }

    .form-panel {
      padding: 16px;
      margin-bottom: 16px;
    }

    .form-grid {
      display: grid;
      grid-template-columns: minmax(180px, 1.2fr) minmax(150px, 1fr) 110px minmax(150px, 1fr) minmax(180px, 1fr);
      gap: 10px;
    }

    label {
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 600;
    }

    input,
    select {
      width: 100%;
      min-height: 42px;
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 9px 11px;
      color: var(--text);
      font: inherit;
      background: #fff;
    }

    input:focus,
    select:focus {
      border-color: var(--primary);
      outline: 2px solid rgba(36, 87, 166, 0.16);
    }

    .form-actions {
      display: flex;
      gap: 10px;
      margin-top: 12px;
    }

    .form-actions.hidden {
      display: none;
    }

    button {
      min-height: 40px;
      border: 1px solid transparent;
      border-radius: 7px;
      padding: 9px 12px;
      font: inherit;
      font-weight: 650;
      cursor: pointer;
      background: #eef2f7;
      color: var(--text);
    }

    button:hover {
      filter: brightness(0.97);
    }

    .primary {
      background: var(--primary);
      color: #fff;
    }

    .primary:hover {
      background: var(--primary-dark);
      filter: none;
    }

    .success {
      background: #e4f3eb;
      color: var(--ok);
      border-color: #b7dfc8;
    }

    .danger {
      background: #fff1ef;
      color: var(--danger);
      border-color: #f4c7c0;
    }

    .tabs {
      display: none;
      margin-bottom: 12px;
      gap: 8px;
    }

    .tabs button {
      flex: 1;
      border-color: var(--line);
    }

    .tabs .active {
      background: var(--primary);
      color: #fff;
      border-color: var(--primary);
    }

    .lists {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    .list-panel {
      min-width: 0;
      overflow: hidden;
    }

    .list-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
    }

    h2 {
      margin: 0;
      font-size: 18px;
    }

    .count {
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }

    .search {
      margin: 12px 16px 0;
    }

    .list-tools {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      align-items: center;
      padding: 12px 16px 0;
    }

    .list-tools .search {
      margin: 0;
    }

    .items {
      display: grid;
      gap: 10px;
      padding: 16px;
    }

    .book {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #fff;
    }

    .book-title {
      margin: 0 0 4px;
      font-size: 16px;
      line-height: 1.25;
      overflow-wrap: anywhere;
    }

    .meta {
      color: var(--muted);
      font-size: 14px;
      overflow-wrap: anywhere;
    }

    .note {
      margin-top: 7px;
      color: #475569;
      font-size: 14px;
      overflow-wrap: anywhere;
    }

    .book-actions {
      display: flex;
      gap: 8px;
      margin-top: 10px;
      flex-wrap: wrap;
    }

    .book-group {
      display: grid;
      gap: 10px;
    }

    .group-heading {
      margin: 4px 0 0;
      padding: 8px 10px;
      border-radius: 7px;
      background: #eef2f7;
      color: #334155;
      font-size: 14px;
      font-weight: 750;
    }

    .series-group {
      display: grid;
      gap: 8px;
      margin-left: 14px;
      padding-left: 12px;
      border-left: 2px solid #d8dee7;
    }

    .series-heading {
      color: #475569;
      font-size: 14px;
      font-weight: 750;
      margin-top: 2px;
    }

    .book-actions button {
      min-height: 36px;
      padding: 7px 10px;
      font-size: 14px;
    }

    .empty {
      padding: 24px 16px;
      color: var(--muted);
      text-align: center;
    }

    .toast {
      position: fixed;
      left: 50%;
      bottom: 18px;
      transform: translateX(-50%);
      max-width: min(520px, calc(100% - 32px));
      padding: 10px 14px;
      border-radius: 7px;
      background: #172033;
      color: #fff;
      box-shadow: var(--shadow);
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.18s ease;
      text-align: center;
    }

    .toast.show {
      opacity: 1;
    }

    @media (max-width: 760px) {
      .page {
        padding: 14px;
      }

      header {
        display: block;
      }

      h1 {
        font-size: 25px;
      }

      .status {
        margin-top: 6px;
        text-align: left;
      }

      .form-grid {
        grid-template-columns: 1fr;
      }

      .list-tools {
        grid-template-columns: 1fr;
      }

      .form-actions {
        display: grid;
        grid-template-columns: 1fr;
      }

      .tabs {
        display: flex;
      }

      .lists {
        display: block;
      }

      .list-panel {
        display: none;
      }

      .list-panel.active {
        display: block;
      }
    }
  </style>
</head>
<body>
  <main class="page">
    <header>
      <div>
        <h1>Домашняя библиотека</h1>
      </div>
      <div class="status" id="status">Загрузка...</div>
    </header>

    <section class="panel form-panel">
      <form id="bookForm" autocomplete="off">
        <div class="form-grid">
          <label>Название
            <input id="title" name="title" required maxlength="180">
          </label>
          <label>Автор
            <input id="author" name="author" maxlength="140" list="authorOptions">
            <datalist id="authorOptions"></datalist>
          </label>
          <label>Год
            <input id="year" name="year" inputmode="numeric" maxlength="20">
          </label>
          <label>Цикл
            <input id="series" name="series" maxlength="160" placeholder="Если есть" list="seriesOptions">
            <datalist id="seriesOptions"></datalist>
          </label>
          <label>Заметка
            <input id="note" name="note" maxlength="240">
          </label>
        </div>
        <div class="form-actions" id="addActions">
          <button class="primary" type="submit" data-action="add" data-target="owned">Добавить в библиотеку</button>
          <button type="submit" data-action="add" data-target="wishlist">Добавить в желаемое</button>
        </div>
        <div class="form-actions hidden" id="editActions">
          <button class="primary" type="submit" data-action="save">Сохранить изменения</button>
          <button type="button" id="cancelEdit">Отменить</button>
        </div>
      </form>
    </section>

    <nav class="tabs" aria-label="Списки книг">
      <button class="active" type="button" data-tab="owned">Мои книги</button>
      <button type="button" data-tab="wishlist">Желаемое</button>
    </nav>

    <section class="lists">
      <article class="panel list-panel active" data-panel="owned">
        <div class="list-head">
          <h2>Мои книги</h2>
          <span class="count" id="ownedCount">0 книг</span>
        </div>
        <div class="list-tools">
          <input class="search" id="ownedSearch" placeholder="Книга, автор или цикл">
        </div>
        <div class="items" id="ownedList"></div>
      </article>

      <article class="panel list-panel" data-panel="wishlist">
        <div class="list-head">
          <h2>Желаемое</h2>
          <span class="count" id="wishlistCount">0 книг</span>
        </div>
        <div class="list-tools">
          <input class="search" id="wishlistSearch" placeholder="Книга, автор или цикл">
        </div>
        <div class="items" id="wishlistList"></div>
      </article>
    </section>
  </main>

  <div class="toast" id="toast"></div>

  <script>
    const state = { owned: [], wishlist: [] };
    const labels = { owned: "библиотеку", wishlist: "желаемое" };
    const form = document.getElementById("bookForm");
    const toast = document.getElementById("toast");
    let editing = null;

    function allBooks() {
      return [...state.owned, ...state.wishlist];
    }

    function showToast(message) {
      toast.textContent = message;
      toast.classList.add("show");
      window.clearTimeout(showToast.timer);
      showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 2200);
    }

    function pluralBooks(count) {
      const last = count % 10;
      const lastTwo = count % 100;
      if (last === 1 && lastTwo !== 11) return `${count} книга`;
      if (last >= 2 && last <= 4 && (lastTwo < 12 || lastTwo > 14)) return `${count} книги`;
      return `${count} книг`;
    }

    function bookMatches(book, query) {
      if (!query) return true;
      const text = `${book.title} ${book.author} ${book.series}`;
      return normalizeSearch(text).includes(normalizeSearch(query));
    }

    function normalizeSearch(value) {
      return String(value || "").toLowerCase().replaceAll("ё", "е").trim();
    }

    function escapeText(value) {
      return String(value || "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
      }[char]));
    }

    function sortValue(value) {
      return String(value || "").trim().toLocaleLowerCase("ru");
    }

    function compareBooks(left, right) {
      return (
        sortValue(left.book.author).localeCompare(sortValue(right.book.author), "ru", { numeric: true }) ||
        sortValue(left.book.series).localeCompare(sortValue(right.book.series), "ru", { numeric: true }) ||
        sortValue(left.book.title).localeCompare(sortValue(right.book.title), "ru", { numeric: true })
      );
    }

    function sortedItems(items) {
      return [...items].sort(compareBooks);
    }

    function uniqueSorted(values) {
      return Array.from(new Set(values.map((value) => String(value || "").trim()).filter(Boolean)))
        .sort((left, right) => left.localeCompare(right, "ru", { numeric: true }));
    }

    function renderOptions(datalistId, values) {
      document.getElementById(datalistId).innerHTML = values
        .map((value) => `<option value="${escapeText(value)}"></option>`)
        .join("");
    }

    function updateAuthorOptions() {
      renderOptions("authorOptions", uniqueSorted(allBooks().map((book) => book.author)));
    }

    function updateSeriesOptions() {
      const selectedAuthor = form.author.value.trim();
      const books = allBooks();
      const source = selectedAuthor
        ? books.filter((book) => book.author === selectedAuthor)
        : books;
      renderOptions("seriesOptions", uniqueSorted(source.map((book) => book.series)));
    }

    function updateFormOptions() {
      updateAuthorOptions();
      updateSeriesOptions();
    }

    function renderBook(target, book, index) {
        const meta = [book.author, book.year].filter(Boolean).join(" · ");
        const series = book.series ? `<div class="meta">Цикл: ${escapeText(book.series)}</div>` : "";
        const moveButton = target === "wishlist"
          ? `<button class="success" type="button" data-action="move" data-index="${index}">Перенести в библиотеку</button>`
          : "";
        return `
          <div class="book">
            <h3 class="book-title">${escapeText(book.title)}</h3>
            ${meta ? `<div class="meta">${escapeText(meta)}</div>` : ""}
            ${series}
            ${book.note ? `<div class="note">${escapeText(book.note)}</div>` : ""}
            <div class="book-actions">
              ${moveButton}
              <button type="button" data-action="order-up" data-target="${target}" data-index="${index}">Вверх</button>
              <button type="button" data-action="order-down" data-target="${target}" data-index="${index}">Вниз</button>
              <button type="button" data-action="edit" data-target="${target}" data-index="${index}">Редактировать</button>
              <button class="danger" type="button" data-action="delete" data-target="${target}" data-index="${index}">Удалить</button>
            </div>
          </div>
        `;
    }

    function renderGrouped(target, visible, field, fallback) {
      const groups = new Map();
      visible.forEach((item) => {
        const key = item.book[field] || fallback;
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(item);
      });

      return Array.from(groups.entries())
        .sort(([keyA], [keyB]) => keyA.localeCompare(keyB, "ru", { numeric: true }))
        .map(([key, items]) => `
          <section class="book-group">
            <div class="group-heading">${escapeText(key)} · ${pluralBooks(items.length)}</div>
            ${sortedItems(items).map(({ book, index }) => renderBook(target, book, index)).join("")}
          </section>
        `).join("");
    }

    function renderAuthorSeriesTree(target, visible) {
      const authorGroups = new Map();
      visible.forEach((item) => {
        const author = item.book.author || "Автор не указан";
        const series = item.book.series || "Без цикла";
        if (!authorGroups.has(author)) authorGroups.set(author, new Map());
        const seriesGroups = authorGroups.get(author);
        if (!seriesGroups.has(series)) seriesGroups.set(series, []);
        seriesGroups.get(series).push(item);
      });

      return Array.from(authorGroups.entries())
        .sort(([authorA], [authorB]) => authorA.localeCompare(authorB, "ru", { numeric: true }))
        .map(([author, seriesGroups]) => {
          const total = Array.from(seriesGroups.values()).reduce((sum, items) => sum + items.length, 0);
          const seriesHtml = Array.from(seriesGroups.entries())
            .sort(([seriesA], [seriesB]) => seriesA.localeCompare(seriesB, "ru", { numeric: true }))
            .map(([series, items]) => `
              <section class="series-group">
                <div class="series-heading">${escapeText(series)} · ${pluralBooks(items.length)}</div>
                ${items.map(({ book, index }) => renderBook(target, book, index)).join("")}
              </section>
            `).join("");

          return `
            <section class="book-group">
              <div class="group-heading">${escapeText(author)} · ${pluralBooks(total)}</div>
              ${seriesHtml}
            </section>
          `;
        }).join("");
    }

    function renderList(target) {
      const list = document.getElementById(`${target}List`);
      const query = document.getElementById(`${target}Search`).value.trim();
      const books = state[target];
      const visible = books
        .map((book, index) => ({ book, index }))
        .filter((item) => bookMatches(item.book, query));
      const sorted = sortedItems(visible);

      document.getElementById(`${target}Count`).textContent = pluralBooks(books.length);

      if (!visible.length) {
        list.innerHTML = `<div class="empty">${query ? "Ничего не найдено" : "Пока пусто"}</div>`;
        return;
      }

      list.innerHTML = renderAuthorSeriesTree(target, visible);
    }

    function render() {
      updateFormOptions();
      renderList("owned");
      renderList("wishlist");
      document.getElementById("status").textContent =
        `В библиотеке: ${state.owned.length} | В желаемом: ${state.wishlist.length}`;
    }

    async function requestJson(url, options = {}) {
      const response = await fetch(url, {
        headers: { "Content-Type": "application/json" },
        ...options
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Ошибка запроса");
      }
      return data;
    }

    async function loadBooks() {
      const data = await requestJson("/api/books");
      state.owned = data.owned || [];
      state.wishlist = data.wishlist || [];
      render();
    }

    async function addBook(target) {
      const payload = {
        ...currentPayload(),
        target
      };

      if (!payload.title) {
        showToast("Введите название книги");
        form.title.focus();
        return;
      }

      await requestJson("/api/books", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      form.reset();
      form.title.focus();
      await loadBooks();
      showToast(`Книга добавлена в ${labels[target]}`);
    }

    function currentPayload() {
      return {
        title: form.title.value.trim(),
        author: form.author.value.trim(),
        year: form.year.value.trim(),
        series: form.series.value.trim(),
        note: form.note.value.trim()
      };
    }

    function setEditMode(target, index) {
      const book = state[target][index];
      if (!book) return;

      editing = { target, index };
      form.title.value = book.title || "";
      form.author.value = book.author || "";
      form.year.value = book.year || "";
      form.series.value = book.series || "";
      form.note.value = book.note || "";
      updateSeriesOptions();
      document.getElementById("addActions").classList.add("hidden");
      document.getElementById("editActions").classList.remove("hidden");
      form.title.focus();
      window.scrollTo({ top: 0, behavior: "smooth" });
    }

    function clearEditMode() {
      editing = null;
      form.reset();
      document.getElementById("editActions").classList.add("hidden");
      document.getElementById("addActions").classList.remove("hidden");
    }

    async function saveEditedBook() {
      if (!editing) return;

      const payload = currentPayload();

      if (!payload.title) {
        showToast("Введите название книги");
        form.title.focus();
        return;
      }

      await requestJson(`/api/books?target=${encodeURIComponent(editing.target)}&index=${editing.index}`, {
        method: "PUT",
        body: JSON.stringify(payload)
      });
      clearEditMode();
      await loadBooks();
      showToast("Книга обновлена");
    }

    async function deleteBook(target, index) {
      const book = state[target][index];
      if (!book || !confirm(`Удалить "${book.title}"?`)) return;

      await requestJson(`/api/books?target=${encodeURIComponent(target)}&index=${index}`, {
        method: "DELETE"
      });
      await loadBooks();
      showToast("Книга удалена");
    }

    async function moveBook(index) {
      await requestJson("/api/move", {
        method: "POST",
        body: JSON.stringify({ index })
      });
      await loadBooks();
      showToast("Книга перенесена в библиотеку");
    }

    async function reorderBook(target, index, direction) {
      await requestJson("/api/reorder", {
        method: "POST",
        body: JSON.stringify({ target, index, direction })
      });
      await loadBooks();
      showToast("Порядок обновлен");
    }

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const action = event.submitter?.dataset.action || "add";
      if (action === "save") {
        saveEditedBook().catch((error) => showToast(error.message));
        return;
      }
      const target = event.submitter?.dataset.target || "owned";
      addBook(target).catch((error) => showToast(error.message));
    });

    document.getElementById("cancelEdit").addEventListener("click", clearEditMode);

    document.querySelectorAll(".search").forEach((input) => {
      input.addEventListener("input", render);
    });

    form.author.addEventListener("input", updateSeriesOptions);
    form.author.addEventListener("change", updateSeriesOptions);

    document.querySelectorAll("[data-tab]").forEach((button) => {
      button.addEventListener("click", () => {
        document.querySelectorAll("[data-tab]").forEach((item) => item.classList.remove("active"));
        document.querySelectorAll("[data-panel]").forEach((item) => item.classList.remove("active"));
        button.classList.add("active");
        document.querySelector(`[data-panel="${button.dataset.tab}"]`).classList.add("active");
      });
    });

    document.querySelector(".lists").addEventListener("click", (event) => {
      const button = event.target.closest("button[data-action]");
      if (!button) return;

      const index = Number(button.dataset.index);
      if (button.dataset.action === "delete") {
        deleteBook(button.dataset.target, index).catch((error) => showToast(error.message));
      }
      if (button.dataset.action === "edit") {
        setEditMode(button.dataset.target, index);
      }
      if (button.dataset.action === "order-up") {
        reorderBook(button.dataset.target, index, "up").catch((error) => showToast(error.message));
      }
      if (button.dataset.action === "order-down") {
        reorderBook(button.dataset.target, index, "down").catch((error) => showToast(error.message));
      }
      if (button.dataset.action === "move") {
        moveBook(index).catch((error) => showToast(error.message));
      }
    });

    loadBooks().catch((error) => {
      document.getElementById("status").textContent = "Ошибка загрузки";
      showToast(error.message);
    });
  </script>
</body>
</html>
"""


def default_data():
    return {"owned": [], "wishlist": []}


def normalize_book(item):
    if not isinstance(item, dict):
        return None
    return {
        "title": str(item.get("title", "")).strip(),
        "author": str(item.get("author", "")).strip(),
        "year": str(item.get("year", "")).strip(),
        "series": str(item.get("series", "")).strip(),
        "note": str(item.get("note", "")).strip(),
    }


def load_data():
    if not DATA_FILE.exists():
        return default_data()

    try:
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_data()

    data = default_data()
    for key in VALID_LISTS:
        if isinstance(raw.get(key), list):
            data[key] = [
                book for book in (normalize_book(item) for item in raw[key])
                if book and book["title"]
            ]
    return data


def save_data(data):
    DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_lan_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


class LibraryHandler(BaseHTTPRequestHandler):
    server_version = "LibraryHTTP/1.0"

    def log_message(self, format, *args):
        return

    def send_text(self, body, status=HTTPStatus.OK, content_type="text/html; charset=utf-8"):
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_json(self, body, status=HTTPStatus.OK):
        self.send_text(
            json.dumps(body, ensure_ascii=False),
            status=status,
            content_type="application/json; charset=utf-8",
        )

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self.send_text(INDEX_HTML)
            return
        if path == "/api/books":
            self.send_json(load_data())
            return
        self.send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self):
        path = urlparse(self.path).path
        body = self.read_json_body()
        if body is None:
            self.send_json({"error": "Invalid JSON"}, status=HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/books":
            self.add_book(body)
            return
        if path == "/api/move":
            self.move_book(body)
            return
        if path == "/api/reorder":
            self.reorder_book(body)
            return
        self.send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_PUT(self):
        path = urlparse(self.path).path
        body = self.read_json_body()
        if body is None:
            self.send_json({"error": "Invalid JSON"}, status=HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/books":
            self.update_book(body)
            return
        self.send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path != "/api/books":
            self.send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return

        query = parse_qs(urlparse(self.path).query)
        target = query.get("target", [""])[0]
        try:
            index = int(query.get("index", ["-1"])[0])
        except ValueError:
            index = -1

        if target not in VALID_LISTS:
            self.send_json({"error": "Unknown list"}, status=HTTPStatus.BAD_REQUEST)
            return

        data = load_data()
        if index < 0 or index >= len(data[target]):
            self.send_json({"error": "Book not found"}, status=HTTPStatus.NOT_FOUND)
            return

        del data[target][index]
        save_data(data)
        self.send_json(data)

    def add_book(self, body):
        target = body.get("target")
        if target not in VALID_LISTS:
            self.send_json({"error": "Unknown list"}, status=HTTPStatus.BAD_REQUEST)
            return

        book = normalize_book(body)
        if not book or not book["title"]:
            self.send_json({"error": "Title is required"}, status=HTTPStatus.BAD_REQUEST)
            return

        data = load_data()
        data[target].append(book)
        save_data(data)
        self.send_json(data, status=HTTPStatus.CREATED)

    def update_book(self, body):
        query = parse_qs(urlparse(self.path).query)
        target = query.get("target", [""])[0]
        try:
            index = int(query.get("index", ["-1"])[0])
        except ValueError:
            index = -1

        if target not in VALID_LISTS:
            self.send_json({"error": "Unknown list"}, status=HTTPStatus.BAD_REQUEST)
            return

        book = normalize_book(body)
        if not book or not book["title"]:
            self.send_json({"error": "Title is required"}, status=HTTPStatus.BAD_REQUEST)
            return

        data = load_data()
        if index < 0 or index >= len(data[target]):
            self.send_json({"error": "Book not found"}, status=HTTPStatus.NOT_FOUND)
            return

        data[target][index] = book
        save_data(data)
        self.send_json(data)

    def move_book(self, body):
        try:
            index = int(body.get("index", -1))
        except (TypeError, ValueError):
            index = -1

        data = load_data()
        if index < 0 or index >= len(data["wishlist"]):
            self.send_json({"error": "Book not found"}, status=HTTPStatus.NOT_FOUND)
            return

        data["owned"].append(data["wishlist"].pop(index))
        save_data(data)
        self.send_json(data)

    def reorder_book(self, body):
        target = body.get("target")
        direction = body.get("direction")
        try:
            index = int(body.get("index", -1))
        except (TypeError, ValueError):
            index = -1

        if target not in VALID_LISTS:
            self.send_json({"error": "Unknown list"}, status=HTTPStatus.BAD_REQUEST)
            return
        if direction not in {"up", "down"}:
            self.send_json({"error": "Unknown direction"}, status=HTTPStatus.BAD_REQUEST)
            return

        data = load_data()
        books = data[target]
        if index < 0 or index >= len(books):
            self.send_json({"error": "Book not found"}, status=HTTPStatus.NOT_FOUND)
            return

        book = books[index]
        same_group_indexes = [
            item_index
            for item_index, item in enumerate(books)
            if item.get("author", "") == book.get("author", "")
            and item.get("series", "") == book.get("series", "")
        ]
        position = same_group_indexes.index(index)
        new_position = position - 1 if direction == "up" else position + 1

        if new_position < 0 or new_position >= len(same_group_indexes):
            self.send_json(data)
            return

        other_index = same_group_indexes[new_position]
        books[index], books[other_index] = books[other_index], books[index]
        save_data(data)
        self.send_json(data)


def main():
    lan_ip = get_lan_ip()
    server = ThreadingHTTPServer((HOST, PORT), LibraryHandler)
    print("Library server is running.")
    print(f"Open on this computer: http://127.0.0.1:{PORT}")
    print(f"Open on your phone:    http://{lan_ip}:{PORT}")
    print("Keep this window open while using the app.")
    server.serve_forever()


if __name__ == "__main__":
    main()
