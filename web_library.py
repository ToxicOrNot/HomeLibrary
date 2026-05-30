# -*- coding: utf-8 -*-
import json
import mimetypes
import os
import re
import socket
from html import unescape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

from github_backup import safe_backup_if_due, safe_restore_from_github

DATA_DIR = Path(__file__).with_name("data")
DATA_FILE = Path(os.environ.get("DATA_FILE", DATA_DIR / "library_data.json"))
LEGACY_DATA_FILE = Path(__file__).with_name("library_data.json")
ICONS_DIR = Path(__file__).with_name("icons")
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
      --bg: #f4f4f5;
      --panel: #ffffff;
      --text: #27272a;
      --muted: #71717a;
      --line: #d4d4d8;
      --field: #ffffff;
      --button: #e4e4e7;
      --book: #ffffff;
      --soft: #e4e4e7;
      --note: #52525b;
      --success-bg: #e4f3eb;
      --success-line: #b7dfc8;
      --danger-bg: #fff1ef;
      --danger-line: #f4c7c0;
      --warning-bg: #fff7ed;
      --warning-line: #fed7aa;
      --warning: #c2410c;
      --focus: rgba(75, 85, 99, 0.18);
      --primary: #374151;
      --primary-dark: #111827;
      --danger: #b42318;
      --ok: #1f7a4c;
      --shadow: 0 10px 28px rgba(31, 41, 51, 0.08);
    }

    [data-theme="dark"] {
      color-scheme: dark;
      --bg: #18181b;
      --panel: #27272a;
      --text: #f4f4f5;
      --muted: #a1a1aa;
      --line: #52525b;
      --field: #18181b;
      --button: #3f3f46;
      --book: #202023;
      --soft: #3f3f46;
      --note: #d4d4d8;
      --success-bg: #173727;
      --success-line: #2f6848;
      --danger-bg: #3b1d1d;
      --danger-line: #704040;
      --warning-bg: #431f0c;
      --warning-line: #9a3412;
      --warning: #fdba74;
      --focus: rgba(203, 213, 225, 0.22);
      --primary: #d1d5db;
      --primary-dark: #f9fafb;
      --danger: #fca5a5;
      --ok: #86efac;
      --shadow: 0 10px 28px rgba(0, 0, 0, 0.28);
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

    .header-actions {
      display: grid;
      justify-items: end;
      gap: 8px;
    }

    .theme-toggle {
      min-height: 34px;
      padding: 6px 10px;
      border-color: var(--line);
      color: var(--text);
      background: var(--button);
      font-size: 13px;
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
      grid-template-columns: minmax(220px, 1.2fr) minmax(170px, 1fr) minmax(170px, 1fr) minmax(120px, 0.45fr);
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
      background: var(--field);
    }

    input:focus,
    select:focus {
      border-color: var(--primary);
      outline: 2px solid var(--focus);
    }

    .form-actions {
      display: flex;
      gap: 10px;
      margin-top: 12px;
    }

    .hidden {
      display: none;
    }

    .form-options {
      display: flex;
      gap: 10px;
      margin-top: 12px;
      align-items: center;
      flex-wrap: wrap;
    }

    .checkbox-label {
      display: inline-flex;
      grid-template-columns: none;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 650;
    }

    .checkbox-label input {
      width: 18px;
      min-height: 18px;
      height: 18px;
      padding: 0;
      accent-color: var(--primary);
    }

    .series-count-field input {
      max-width: 120px;
    }

    button {
      min-height: 40px;
      border: 1px solid transparent;
      border-radius: 7px;
      padding: 9px 12px;
      font: inherit;
      font-weight: 650;
      cursor: pointer;
      background: var(--button);
      color: var(--text);
    }

    button:hover {
      filter: brightness(0.97);
    }

    .primary {
      background: var(--primary);
      color: #fff;
    }

    [data-theme="dark"] .primary,
    [data-theme="dark"] .tabs .active {
      color: #111827;
    }

    .primary:hover {
      background: var(--primary-dark);
      filter: none;
    }

    .success {
      background: var(--success-bg);
      color: var(--ok);
      border-color: var(--success-line);
    }

    .danger {
      background: var(--danger-bg);
      color: var(--danger);
      border-color: var(--danger-line);
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

    .global-search-panel {
      padding: 12px 16px;
      margin-bottom: 16px;
    }

    .global-search-panel .search {
      margin: 0;
      padding-right: 38px;
    }

    .search-wrap {
      position: relative;
    }

    .clear-search {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      position: absolute;
      top: 50%;
      right: 8px;
      width: 28px;
      min-width: 28px;
      height: 28px;
      min-height: 28px;
      padding: 0;
      border: 0;
      border-radius: 50%;
      background: transparent;
      color: var(--muted);
      font-size: 20px;
      line-height: 1;
      opacity: 0;
      pointer-events: none;
      transform: translateY(-50%);
      transition: opacity 0.15s ease, background 0.15s ease;
    }

    .clear-search.show {
      opacity: 0.45;
      pointer-events: auto;
    }

    .clear-search.show:hover {
      opacity: 0.8;
      background: var(--button);
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
      background: var(--book);
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
      color: var(--note);
      font-size: 14px;
      overflow-wrap: anywhere;
    }

    .book-actions {
      display: flex;
      gap: 8px;
      margin-top: 10px;
      flex-wrap: wrap;
      align-items: center;
    }

    .rating-select {
      min-height: 36px;
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 6px 8px;
      font: inherit;
      font-size: 14px;
      background: var(--field);
    }

    .rating-field {
      display: grid;
      gap: 3px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
    }

    .book-group {
      display: grid;
      gap: 10px;
    }

    .group-heading {
      margin: 4px 0 0;
      padding: 8px 10px;
      border-radius: 7px;
      background: var(--soft);
      color: var(--text);
      font-size: 14px;
      font-weight: 750;
    }

    .series-group {
      display: grid;
      gap: 8px;
      margin-left: 14px;
      padding-left: 12px;
      border-left: 2px solid var(--line);
    }

    .series-heading {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      color: var(--note);
      font-size: 14px;
      font-weight: 750;
      margin-top: 2px;
    }

    .series-meta {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      font-weight: 650;
    }

    .series-count-input {
      width: 74px;
      min-height: 30px;
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 4px 7px;
      font: inherit;
      font-size: 13px;
      background: var(--field);
    }

    .complete-badge {
      padding: 4px 7px;
      border-radius: 7px;
      background: var(--success-bg);
      color: var(--ok);
      font-size: 12px;
      font-weight: 800;
      white-space: nowrap;
    }

    .ongoing-badge {
      padding: 4px 7px;
      border: 1px solid var(--warning-line);
      border-radius: 7px;
      background: var(--warning-bg);
      color: var(--warning);
      font-size: 12px;
      font-weight: 800;
      white-space: nowrap;
    }

    .book-actions button {
      min-height: 36px;
      padding: 7px 10px;
      font-size: 14px;
    }

    .book-info {
      margin-top: 10px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: var(--soft);
      color: var(--note);
      font-size: 14px;
    }

    .info-title {
      margin-bottom: 6px;
      color: var(--text);
      font-weight: 750;
    }

    .info-row {
      margin-top: 5px;
      overflow-wrap: anywhere;
    }

    .info-link {
      display: inline-block;
      margin-top: 8px;
      color: var(--primary);
      font-weight: 750;
      text-decoration: none;
    }

    .icon-button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      min-width: 36px;
      padding: 7px 0;
      font-size: 17px;
      line-height: 1;
    }

    .icon-button img,
    .scroll-top img {
      width: 20px;
      height: 20px;
      display: block;
      flex: 0 0 auto;
      object-fit: contain;
    }

    .scroll-top img {
      width: 24px;
      height: 24px;
    }

    .empty {
      padding: 24px 16px;
      color: var(--muted);
      text-align: center;
    }

    .load-more {
      display: grid;
      gap: 8px;
      justify-items: center;
      padding: 8px 0 2px;
      color: var(--muted);
      font-size: 13px;
    }

    .load-more button {
      min-width: 180px;
    }

    .toast {
      position: fixed;
      left: 50%;
      bottom: 18px;
      transform: translateX(-50%);
      max-width: min(520px, calc(100% - 32px));
      padding: 10px 14px;
      border-radius: 7px;
      background: #18181b;
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

    .scroll-top {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      position: fixed;
      right: 18px;
      bottom: 18px;
      z-index: 20;
      width: 42px;
      min-width: 42px;
      height: 42px;
      padding: 0;
      border-radius: 7px;
      box-shadow: var(--shadow);
      opacity: 0;
      pointer-events: none;
      transform: translateY(8px);
      transition: opacity 0.18s ease, transform 0.18s ease;
    }

    .scroll-top.show {
      opacity: 1;
      pointer-events: auto;
      transform: translateY(0);
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

      .header-actions {
        justify-items: start;
        margin-top: 8px;
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

      .scroll-top {
        right: 14px;
        bottom: 14px;
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
      <div class="header-actions">
        <button class="theme-toggle" type="button" id="themeToggle">Темная тема</button>
        <div class="status" id="status">Загрузка...</div>
      </div>
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
          <label>Цикл
            <input id="series" name="series" maxlength="160" placeholder="Если есть" list="seriesOptions">
            <datalist id="seriesOptions"></datalist>
          </label>
          <label class="series-count-field" id="seriesCountField">Книг в цикле
            <input id="seriesCount" name="series_count" type="number" min="0" step="1" inputmode="numeric" disabled>
          </label>
        </div>
        <div class="form-actions" id="addActions">
          <button class="primary" type="submit" data-action="add" data-target="owned">Добавить в библиотеку</button>
          <button type="submit" data-action="add" data-target="wishlist">Добавить в желаемое</button>
        </div>
        <div class="form-options" id="addOptions">
          <label class="checkbox-label">
            <input type="checkbox" id="keepAuthorSeries">
            Не сбрасывать автора и цикл
          </label>
        </div>
        <div class="form-actions hidden" id="editActions">
          <button class="primary" type="submit" data-action="save">Сохранить изменения</button>
          <button type="button" id="cancelEdit">Отменить</button>
        </div>
      </form>
    </section>

    <section class="panel global-search-panel">
      <div class="search-wrap">
        <input class="search" id="globalSearch" placeholder="Поиск по библиотеке и желаемому">
        <button class="clear-search" type="button" id="clearSearch" title="Очистить поиск" aria-label="Очистить поиск">×</button>
      </div>
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
        <div class="items" id="ownedList"></div>
      </article>

      <article class="panel list-panel" data-panel="wishlist">
        <div class="list-head">
          <h2>Желаемое</h2>
          <span class="count" id="wishlistCount">0 книг</span>
        </div>
        <div class="items" id="wishlistList"></div>
      </article>
    </section>
  </main>

  <div class="toast" id="toast"></div>
  <button class="primary scroll-top" type="button" id="scrollTop" title="Наверх" aria-label="Наверх">
    <img id="scrollTopIcon" src="/icons/Arrow%20Big%20Up%20Lines.png?v={{ICON_VERSION}}" alt="">
  </button>

  <script>
    const state = { owned: [], wishlist: [], series_counts: {} };
    const INITIAL_RENDER_LIMIT = 12;
    const RENDER_LIMIT_STEP = 12;
    const renderLimits = { owned: INITIAL_RENDER_LIMIT, wishlist: INITIAL_RENDER_LIMIT };
    const labels = { owned: "библиотеку", wishlist: "желаемое" };
    const form = document.getElementById("bookForm");
    const toast = document.getElementById("toast");
    const scrollTopButton = document.getElementById("scrollTop");
    const scrollTopIcon = document.getElementById("scrollTopIcon");
    const themeToggle = document.getElementById("themeToggle");
    const keepAuthorSeries = document.getElementById("keepAuthorSeries");
    const globalSearch = document.getElementById("globalSearch");
    const clearSearch = document.getElementById("clearSearch");
    const seriesCountField = document.getElementById("seriesCountField");
    let editing = null;

    const iconVersion = "{{ICON_VERSION}}";
    const icons = {
      light: {
        info: "Info%20Square%20Rounded.png",
        up: "Arrow%20Big%20Up.png",
        down: "Arrow%20Big%20Down.png",
        edit: "Edit.png",
        trash: "Trash.png",
        top: "Arrow%20Big%20Up%20Lines.png"
      },
      dark: {
        info: "Info.png",
        up: "Arrow%20Big%20Up%201.png",
        down: "Arrow%20Big%20Down%201.png",
        edit: "Edit%201.png",
        trash: "Trash%201.png",
        top: "Arrow%20Big%20Up%20Lines%201.png"
      }
    };

    function allBooks() {
      return [...state.owned, ...state.wishlist];
    }

    function showToast(message) {
      toast.textContent = message;
      toast.classList.add("show");
      window.clearTimeout(showToast.timer);
      showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 2200);
    }

    function currentTheme() {
      return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
    }

    function iconSrc(name) {
      return `/icons/${icons[currentTheme()][name]}?v=${iconVersion}`;
    }

    function applyTheme(theme) {
      const normalized = theme === "dark" ? "dark" : "light";
      document.documentElement.dataset.theme = normalized;
      localStorage.setItem("libraryTheme", normalized);
      themeToggle.textContent = normalized === "dark" ? "Светлая тема" : "Темная тема";
      scrollTopIcon.src = iconSrc("top");
    }

    applyTheme(localStorage.getItem("libraryTheme") || "dark");

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
      updateSeriesCountInput();
    }

    function updateSeriesCountInput() {
      const hasSeries = Boolean(form.series.value.trim());
      form.seriesCount.disabled = !hasSeries;
      if (!hasSeries) {
        form.seriesCount.value = "";
      }
    }

    function updateFormOptions() {
      updateAuthorOptions();
      updateSeriesOptions();
    }

    function renderBook(target, book, index) {
        const meta = [book.author].filter(Boolean).join(" · ");
        const series = book.series ? `<div class="meta">Цикл: ${escapeText(book.series)}</div>` : "";
        const moveButton = target === "wishlist"
          ? `<button class="success" type="button" data-action="move" data-index="${index}">Перенести в библиотеку</button>`
          : "";
        const ratingControls = target === "owned"
          ? `
              <label class="rating-field">Пингвинчик
                <select class="rating-select" data-action="rating" data-rating-field="rating_penguin" data-target="${target}" data-index="${index}" title="Пингвинчик">
                  ${ratingOptions(book.rating_penguin)}
                </select>
              </label>
              <label class="rating-field">Цыпка
                <select class="rating-select" data-action="rating" data-rating-field="rating_chick" data-target="${target}" data-index="${index}" title="Цыпка">
                  ${ratingOptions(book.rating_chick)}
                </select>
              </label>
            `
          : "";
        return `
          <div class="book">
            <h3 class="book-title">${escapeText(book.title)}</h3>
            ${meta ? `<div class="meta">${escapeText(meta)}</div>` : ""}
            ${series}
            <div class="book-actions">
              ${ratingControls}
              ${moveButton}
              <button class="icon-button" type="button" data-action="info" data-target="${target}" data-index="${index}" title="LiveLib" aria-label="LiveLib"><img src="${iconSrc("info")}" alt=""></button>
              <button class="icon-button" type="button" data-action="order-up" data-target="${target}" data-index="${index}" title="Вверх" aria-label="Вверх"><img src="${iconSrc("up")}" alt=""></button>
              <button class="icon-button" type="button" data-action="order-down" data-target="${target}" data-index="${index}" title="Вниз" aria-label="Вниз"><img src="${iconSrc("down")}" alt=""></button>
              <button class="icon-button" type="button" data-action="edit" data-target="${target}" data-index="${index}" title="Редактировать" aria-label="Редактировать"><img src="${iconSrc("edit")}" alt=""></button>
              <button class="icon-button danger" type="button" data-action="delete" data-target="${target}" data-index="${index}" title="Удалить" aria-label="Удалить"><img src="${iconSrc("trash")}" alt=""></button>
            </div>
            <div class="book-info" id="info-${target}-${index}" hidden></div>
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

    function seriesKey(author, series) {
      return `${author || ""}\u001f${series || ""}`;
    }

    function seriesTotal(author, series) {
      return [...state.owned, ...state.wishlist].filter((book) =>
        (book.author || "Автор не указан") === author &&
        (book.series || "Без цикла") === series
      ).length;
    }

    function seriesListTotal(target, author, series) {
      return state[target].filter((book) =>
        (book.author || "Автор не указан") === author &&
        (book.series || "Без цикла") === series
      ).length;
    }

    function seriesCountLabel(target, author, series) {
      const currentCount = seriesListTotal(target, author, series);
      const otherTarget = target === "owned" ? "wishlist" : "owned";
      const otherCount = seriesListTotal(otherTarget, author, series);
      const otherLabel = target === "owned" ? "в желаемом" : "в библиотеке";
      const extra = otherCount > 0 ? ` (${pluralBooks(otherCount)} ${otherLabel})` : "";
      return `${pluralBooks(currentCount)}${extra}`;
    }

    function renderSeriesHeading(target, author, series, visibleCount) {
      const countLabel = seriesCountLabel(target, author, series);
      if (series === "Без цикла") {
        return `<div class="series-heading"><span>${escapeText(series)} · ${escapeText(countLabel)}</span></div>`;
      }

      const key = seriesKey(author, series);
      const expected = Number(state.series_counts[key] || 0);
      const total = seriesTotal(author, series);
      const status = expected > 0 && expected === total
        ? `<span class="complete-badge">Цикл завершен</span>`
        : expected > total
          ? `<span class="ongoing-badge">Ongoing</span>`
        : "";

      return `
        <div class="series-heading">
          <span>${escapeText(series)} · ${escapeText(countLabel)}</span>
          <span class="series-meta">
            <span>Книг в цикле</span>
            <input class="series-count-input" type="number" min="0" step="1"
              value="${expected || ""}"
              data-author="${escapeText(author)}"
              data-series="${escapeText(series)}">
            ${status}
          </span>
        </div>
      `;
    }

    function renderAuthorSeriesTree(target, visible, limit) {
      const authorGroups = new Map();
      visible.forEach((item) => {
        const author = item.book.author || "Автор не указан";
        const series = item.book.series || "Без цикла";
        if (!authorGroups.has(author)) authorGroups.set(author, new Map());
        const seriesGroups = authorGroups.get(author);
        if (!seriesGroups.has(series)) seriesGroups.set(series, []);
        seriesGroups.get(series).push(item);
      });

      let renderedSeries = 0;
      let renderedBooks = 0;
      const html = [];
      const authors = Array.from(authorGroups.entries())
        .sort(([authorA], [authorB]) => authorA.localeCompare(authorB, "ru", { numeric: true }));
      const totalSeries = authors.reduce((sum, [, seriesGroups]) => sum + seriesGroups.size, 0);

      for (const [author, seriesGroups] of authors) {
        if (renderedSeries >= limit) break;

        const renderedSeriesHtml = [];
        let authorRenderedTotal = 0;
        const seriesEntries = Array.from(seriesGroups.entries())
          .sort(([seriesA], [seriesB]) => seriesA.localeCompare(seriesB, "ru", { numeric: true }));

        for (const [series, items] of seriesEntries) {
          if (renderedSeries >= limit) break;
          renderedSeries += 1;
          renderedBooks += items.length;
          authorRenderedTotal += items.length;
          renderedSeriesHtml.push(`
              <section class="series-group">
                ${renderSeriesHeading(target, author, series, items.length)}
                ${items.map(({ book, index }) => renderBook(target, book, index)).join("")}
              </section>
          `);
        }

        if (renderedSeriesHtml.length) {
          html.push(`
            <section class="book-group">
              <div class="group-heading">${escapeText(author)} · ${pluralBooks(authorRenderedTotal)}</div>
              ${renderedSeriesHtml.join("")}
            </section>
          `);
        }
      }

      return {
        html: html.join(""),
        renderedSeries,
        renderedBooks,
        totalSeries,
        totalBooks: visible.length
      };
    }

    function renderList(target) {
      const list = document.getElementById(`${target}List`);
      const query = globalSearch.value.trim();
      const books = state[target];
      const visible = books
        .map((book, index) => ({ book, index }))
        .filter((item) => bookMatches(item.book, query));

      document.getElementById(`${target}Count`).textContent = pluralBooks(books.length);

      if (!visible.length) {
        list.innerHTML = `<div class="empty">${query ? "Ничего не найдено" : "Пока пусто"}</div>`;
        return;
      }

      const rendered = renderAuthorSeriesTree(target, visible, renderLimits[target]);
      const more = rendered.totalSeries > rendered.renderedSeries
        ? `
            <div class="load-more">
              <div>Показано ${pluralBooks(rendered.renderedBooks)} из ${pluralBooks(rendered.totalBooks)}</div>
              <button type="button" data-action="show-more" data-target="${target}">
                Показать ещё
              </button>
            </div>
          `
        : "";
      list.innerHTML = rendered.html + more;
    }

    function render() {
      updateFormOptions();
      renderList("owned");
      renderList("wishlist");
      clearSearch.classList.toggle("show", Boolean(globalSearch.value.trim()));
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
      state.series_counts = data.series_counts || {};
      render();
    }

    async function saveSeriesCount(author, series, count) {
      await requestJson("/api/series-count", {
        method: "POST",
        body: JSON.stringify({ author, series, count })
      });
      await loadBooks();
      showToast("Количество книг в цикле сохранено");
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
      resetAfterAdd();
      form.title.focus();
      await loadBooks();
      showToast(`Книга добавлена в ${labels[target]}`);
    }

    function resetAfterAdd() {
      const keepAuthor = keepAuthorSeries.checked;
      const author = form.author.value;
      const series = form.series.value;
      const seriesCount = form.seriesCount.value;
      form.reset();
      keepAuthorSeries.checked = keepAuthor;
      if (keepAuthor) {
        form.author.value = author;
        form.series.value = series;
        form.seriesCount.value = seriesCount;
      }
      updateSeriesOptions();
    }

    function currentPayload() {
      return {
        title: form.title.value.trim(),
        author: form.author.value.trim(),
        series: form.series.value.trim(),
        series_count: form.seriesCount.disabled ? "" : form.seriesCount.value.trim()
      };
    }

    function ratingOptions(current) {
      const normalized = normalizeRating(current);
      const values = ["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"];
      return values.map((value) => {
        const label = value ? value : "Оценка";
        const selected = value === normalized ? "selected" : "";
        return `<option value="${value}" ${selected}>${label}</option>`;
      }).join("");
    }

    function normalizeRating(value) {
      const text = String(value || "").trim();
      const number = Number(text);
      if (Number.isInteger(number) && number >= 1 && number <= 10) {
        return String(number);
      }
      return "";
    }

    async function rateBook(target, index, field, rating) {
      await requestJson("/api/rating", {
        method: "POST",
        body: JSON.stringify({ target, index, field, rating })
      });
      await loadBooks();
      showToast("Оценка сохранена");
    }

    function setEditMode(target, index) {
      const book = state[target][index];
      if (!book) return;

      editing = { target, index };
      form.title.value = book.title || "";
      form.author.value = book.author || "";
      form.series.value = book.series || "";
      form.seriesCount.value = "";
      updateSeriesOptions();
      document.getElementById("addActions").classList.add("hidden");
      document.getElementById("addOptions").classList.add("hidden");
      seriesCountField.classList.add("hidden");
      document.getElementById("editActions").classList.remove("hidden");
      form.title.focus();
      window.scrollTo({ top: 0, behavior: "smooth" });
    }

    function clearEditMode() {
      editing = null;
      form.reset();
      keepAuthorSeries.checked = localStorage.getItem("keepAuthorSeries") === "true";
      document.getElementById("editActions").classList.add("hidden");
      document.getElementById("addActions").classList.remove("hidden");
      document.getElementById("addOptions").classList.remove("hidden");
      seriesCountField.classList.remove("hidden");
      updateSeriesCountInput();
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

    async function showLiveLibInfo(target, index) {
      const panel = document.getElementById(`info-${target}-${index}`);
      const book = state[target]?.[index];
      if (!panel || !book) return;

      if (!panel.hidden && panel.dataset.loaded === "true") {
        panel.hidden = true;
        return;
      }

      panel.hidden = false;
      panel.innerHTML = `<div class="meta">Ищу информацию на LiveLib и Goodreads...</div>`;

      const params = new URLSearchParams({
        title: book.title || "",
        author: book.author || ""
      });
      const data = await requestJson(`/api/livelib?${params.toString()}`);
      panel.dataset.loaded = "true";

      const rows = [];
      if (data.source) {
        rows.push(`<div class="info-row"><strong>Источник:</strong> ${escapeText(data.source)}</div>`);
      }
      if (data.author) {
        rows.push(`<div class="info-row"><strong>Автор:</strong> ${escapeText(data.author)}</div>`);
      }
      if (data.rating) {
        rows.push(`<div class="info-row"><strong>Рейтинг ${escapeText(data.source || "")}:</strong> ${escapeText(data.rating)}</div>`);
      }
      if (data.description) {
        rows.push(`<div class="info-row">${escapeText(data.description)}</div>`);
      }
      if (!rows.length) {
        rows.push(`<div class="info-row">Автоматически получить описание не удалось. Можно открыть поиск LiveLib вручную.</div>`);
      }

      const link = data.url
        ? `<a class="info-link" href="${escapeText(data.url)}" target="_blank" rel="noopener">Открыть на ${escapeText(data.source || "сайте")}</a>`
        : "";
      panel.innerHTML = `
        <div class="info-title">${escapeText(data.title || book.title)}</div>
        ${rows.join("")}
        ${link}
      `;
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

    globalSearch.addEventListener("input", () => {
      renderLimits.owned = INITIAL_RENDER_LIMIT;
      renderLimits.wishlist = INITIAL_RENDER_LIMIT;
      render();
    });

    clearSearch.addEventListener("click", () => {
      globalSearch.value = "";
      renderLimits.owned = INITIAL_RENDER_LIMIT;
      renderLimits.wishlist = INITIAL_RENDER_LIMIT;
      render();
      globalSearch.focus();
    });

    form.author.addEventListener("input", updateSeriesOptions);
    form.author.addEventListener("change", updateSeriesOptions);
    form.series.addEventListener("input", updateSeriesCountInput);
    form.series.addEventListener("change", updateSeriesCountInput);
    updateSeriesCountInput();
    keepAuthorSeries.checked = localStorage.getItem("keepAuthorSeries") === "true";
    keepAuthorSeries.addEventListener("change", () => {
      localStorage.setItem("keepAuthorSeries", keepAuthorSeries.checked ? "true" : "false");
    });

    themeToggle.addEventListener("click", () => {
      applyTheme(currentTheme() === "dark" ? "light" : "dark");
      render();
    });

    document.querySelectorAll("[data-tab]").forEach((button) => {
      button.addEventListener("click", () => {
        document.querySelectorAll("[data-tab]").forEach((item) => item.classList.remove("active"));
        document.querySelectorAll("[data-panel]").forEach((item) => item.classList.remove("active"));
        button.classList.add("active");
        document.querySelector(`[data-panel="${button.dataset.tab}"]`).classList.add("active");
      });
    });

    function updateScrollTopButton() {
      scrollTopButton.classList.toggle("show", window.scrollY > 360);
    }

    scrollTopButton.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });

    window.addEventListener("scroll", updateScrollTopButton, { passive: true });
    updateScrollTopButton();

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
      if (button.dataset.action === "info") {
        showLiveLibInfo(button.dataset.target, index).catch((error) => showToast(error.message));
      }
      if (button.dataset.action === "show-more") {
        renderLimits[button.dataset.target] += RENDER_LIMIT_STEP;
        renderList(button.dataset.target);
      }
    });

    document.querySelector(".lists").addEventListener("change", (event) => {
      const select = event.target.closest("select[data-action='rating']");
      if (select) {
        rateBook(
          select.dataset.target,
          Number(select.dataset.index),
          select.dataset.ratingField,
          select.value
        ).catch((error) => showToast(error.message));
        return;
      }

      const countInput = event.target.closest("input.series-count-input");
      if (countInput) {
        saveSeriesCount(
          countInput.dataset.author,
          countInput.dataset.series,
          countInput.value
        ).catch((error) => showToast(error.message));
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
    return {"owned": [], "wishlist": [], "series_counts": {}}


def normalize_book(item):
    if not isinstance(item, dict):
        return None
    return {
        "title": str(item.get("title", "")).strip(),
        "author": str(item.get("author", "")).strip(),
        "series": str(item.get("series", "")).strip(),
        "rating_penguin": normalize_rating(
            item.get("rating_penguin", item.get("rating", ""))
        ),
        "rating_chick": normalize_rating(item.get("rating_chick", "")),
    }


def normalize_rating(value):
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        rating = int(text)
    except ValueError:
        return ""
    if 1 <= rating <= 10:
        return str(rating)
    return ""


def normalize_duplicate_text(value):
    return " ".join(str(value or "").casefold().split())


def duplicate_book_location(data, book):
    title = normalize_duplicate_text(book.get("title", ""))
    author = normalize_duplicate_text(book.get("author", ""))
    for target, label in (("owned", "библиотеке"), ("wishlist", "желаемом")):
        for item in data.get(target, []):
            if (
                normalize_duplicate_text(item.get("title", "")) == title
                and normalize_duplicate_text(item.get("author", "")) == author
            ):
                return label
    return ""


def existing_series_name(data, author, series):
    normalized_author = normalize_duplicate_text(author)
    normalized_series = normalize_duplicate_text(series)
    if not normalized_series:
        return ""

    for target in VALID_LISTS:
        for item in data.get(target, []):
            if (
                normalize_duplicate_text(item.get("author", "")) == normalized_author
                and normalize_duplicate_text(item.get("series", "")) == normalized_series
                and item.get("series", "").strip()
            ):
                return item.get("series", "").strip()
    return ""


def apply_existing_series_name(data, book):
    existing = existing_series_name(data, book.get("author", ""), book.get("series", ""))
    if existing:
        book["series"] = existing
    return book


def apply_series_count_from_body(data, book, body):
    raw_count = str(body.get("series_count", "") or "").strip()
    if not raw_count or not book.get("series", "").strip():
        return True

    try:
        count = int(raw_count)
    except ValueError:
        return False

    key = series_key(book.get("author", ""), book.get("series", ""))
    data.setdefault("series_counts", {})
    if count > 0:
        data["series_counts"][key] = count
    else:
        data["series_counts"].pop(key, None)
    return True


def normalize_series_counts(value):
    if not isinstance(value, dict):
        return {}

    result = {}
    for key, raw_count in value.items():
        text_key = str(key).strip()
        if not text_key:
            continue
        try:
            count = int(raw_count)
        except (TypeError, ValueError):
            continue
        if count > 0:
            result[text_key] = count
    return result


def series_key(author, series):
    return f"{author or ''}\u001f{series or ''}"


def load_data():
    migrate_legacy_data_file()
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
    data["series_counts"] = normalize_series_counts(raw.get("series_counts", {}))
    return data


def save_data(data, backup=True):
    data["series_counts"] = normalize_series_counts(data.get("series_counts", {}))
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if backup:
        safe_backup_if_due(DATA_FILE, force=True)


def ensure_data_file_schema(backup=True):
    data = load_data()
    changed = False

    if "series_counts" not in data:
        data["series_counts"] = {}
        changed = True

    if not data["series_counts"]:
        legacy_counts = load_legacy_series_counts()
        if legacy_counts:
            data["series_counts"] = legacy_counts
            changed = True

    if changed or not DATA_FILE.exists():
        save_data(data, backup=backup)


def load_legacy_series_counts():
    if not LEGACY_DATA_FILE.exists():
        return {}
    try:
        raw = json.loads(LEGACY_DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return normalize_series_counts(raw.get("series_counts", {}))


def migrate_legacy_data_file():
    if DATA_FILE.exists() or not LEGACY_DATA_FILE.exists():
        return
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(LEGACY_DATA_FILE.read_text(encoding="utf-8"), encoding="utf-8")


def get_lan_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def fetch_book_info(title, author=""):
    livelib_info = fetch_livelib_info(title, author)
    if is_livelib_book_result(livelib_info):
        return livelib_info

    goodreads_info = fetch_goodreads_info(title, author)
    if is_goodreads_book_result(goodreads_info):
        return goodreads_info

    return goodreads_info or livelib_info


def fetch_livelib_info(title, author=""):
    title = str(title or "").strip()
    author = str(author or "").strip()
    query = " ".join(part for part in (title, author) if part).strip()
    search_url = f"https://www.livelib.ru/find/books/{quote_plus(query)}"
    result = {
        "title": title,
        "author": author,
        "url": search_url,
        "source": "LiveLib",
    }

    if not title:
        result["description"] = "Название книги не указано."
        return result

    try:
        html = fetch_url(search_url)
        book_url = first_livelib_book_url(html) or search_url
        if book_url != search_url:
            html = fetch_url(book_url)
        parsed = parse_livelib_book_page(html)
        parsed["url"] = parsed.get("url") or book_url
        return {**result, **parsed}
    except (OSError, HTTPError, URLError, TimeoutError, ValueError):
        result["description"] = (
            "Не удалось автоматически загрузить данные LiveLib. "
            "Откройте поиск вручную."
        )
        return result


def is_livelib_book_result(info):
    return info.get("source") == "LiveLib" and "/book/" in info.get("url", "")


def fetch_goodreads_info(title, author=""):
    title = str(title or "").strip()
    author = str(author or "").strip()
    query = " ".join(part for part in (title, author) if part).strip()
    search_url = f"https://www.goodreads.com/search?q={quote_plus(query)}"
    title_url = f"https://www.goodreads.com/book/title?id={quote_plus(title)}"
    result = {
        "title": title,
        "author": author,
        "url": title_url if title else search_url,
        "source": "Goodreads",
    }

    if not title:
        result["description"] = "Название книги не указано."
        return result

    try:
        html = fetch_url(title_url)
        parsed = parse_livelib_book_page(html)
        if parsed.get("title") or parsed.get("rating") or parsed.get("description"):
            parsed["url"] = parsed.get("url") or title_url
            parsed["source"] = "Goodreads"
            return {**result, **parsed}

        html = fetch_url(search_url)
        book_url = first_goodreads_book_url(html) or search_url
        if book_url != search_url:
            html = fetch_url(book_url)
        parsed = parse_livelib_book_page(html)
        parsed["url"] = parsed.get("url") or book_url
        parsed["source"] = "Goodreads"
        return {**result, **parsed}
    except (OSError, HTTPError, URLError, TimeoutError, ValueError):
        result["description"] = (
            "Не удалось автоматически загрузить данные Goodreads. "
            "Откройте поиск вручную."
        )
        return result


def is_goodreads_book_result(info):
    url = info.get("url", "")
    has_data = bool(info.get("title") or info.get("rating") or info.get("description"))
    return has_data and info.get("source") == "Goodreads" and (
        "/book/show/" in url or "/book/title" in url
    )


def fetch_url(url):
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=10) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def first_livelib_book_url(html):
    match = re.search(r'href=["\']([^"\']*/book/[^"\']+)["\']', html, re.IGNORECASE)
    if not match:
        return ""
    return absolute_livelib_url(unescape(match.group(1)))


def first_goodreads_book_url(html):
    patterns = [
        r'href=["\'](?P<value>/book/show/[^"\']+)["\']',
        r'href=["\'](?P<value>https://www\.goodreads\.com/book/show/[^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return absolute_goodreads_url(unescape(match.group("value")))
    return ""


def absolute_livelib_url(url):
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("/"):
        return f"https://www.livelib.ru{url}"
    return url


def absolute_goodreads_url(url):
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("/"):
        return f"https://www.goodreads.com{url}"
    return url


def parse_livelib_book_page(html):
    json_data = parse_json_ld_book(html)
    if json_data:
        return json_data

    title = meta_content(html, "og:title") or title_tag(html)
    description = meta_content(html, "og:description") or meta_content(html, "description")
    url = meta_content(html, "og:url")
    rating = first_match(
        html,
        [
            r'"ratingValue"\s*:\s*"?(?P<value>[0-9]+(?:[.,][0-9]+)?)',
            r'itemprop=["\']ratingValue["\'][^>]*content=["\'](?P<value>[0-9]+(?:[.,][0-9]+)?)',
        ],
    )
    return compact_book_info(
        {
            "title": clean_html_text(title),
            "description": clean_html_text(description),
            "rating": clean_html_text(rating),
            "url": absolute_livelib_url(clean_html_text(url)) if url else "",
        }
    )


def parse_json_ld_book(html):
    scripts = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    for script in scripts:
        try:
            data = json.loads(unescape(script).strip())
        except json.JSONDecodeError:
            continue
        book = find_json_ld_book(data)
        if not book:
            continue
        author = book.get("author", "")
        if isinstance(author, list):
            author = ", ".join(
                clean_html_text(item.get("name", item)) if isinstance(item, dict) else clean_html_text(item)
                for item in author
            )
        elif isinstance(author, dict):
            author = author.get("name", "")
        rating = book.get("aggregateRating", {})
        if isinstance(rating, dict):
            rating = rating.get("ratingValue", "")
        return compact_book_info(
            {
                "title": clean_html_text(book.get("name", "")),
                "author": clean_html_text(author),
                "description": clean_html_text(book.get("description", "")),
                "rating": clean_html_text(rating),
                "url": absolute_livelib_url(clean_html_text(book.get("url", ""))),
            }
        )
    return {}


def find_json_ld_book(data):
    if isinstance(data, list):
        for item in data:
            found = find_json_ld_book(item)
            if found:
                return found
    if not isinstance(data, dict):
        return None

    item_type = data.get("@type")
    if isinstance(item_type, list):
        is_book = any(str(value).lower() == "book" for value in item_type)
    else:
        is_book = str(item_type).lower() == "book"
    if is_book:
        return data

    graph = data.get("@graph")
    if graph:
        return find_json_ld_book(graph)
    return None


def meta_content(html, name):
    patterns = [
        rf'<meta[^>]+property=["\']{re.escape(name)}["\'][^>]+content=["\'](?P<value>.*?)["\']',
        rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\'](?P<value>.*?)["\']',
        rf'<meta[^>]+content=["\'](?P<value>.*?)["\'][^>]+(?:property|name)=["\']{re.escape(name)}["\']',
    ]
    return first_match(html, patterns)


def title_tag(html):
    return first_match(html, [r"<title[^>]*>(?P<value>.*?)</title>"])


def first_match(text, patterns):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group("value")
    return ""


def clean_html_text(value, limit=700):
    text = unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[:limit].rsplit(" ", 1)[0] + "..."
    return text


def compact_book_info(info):
    return {key: value for key, value in info.items() if value}


def icon_version():
    try:
        return str(max(path.stat().st_mtime_ns for path in ICONS_DIR.glob("*.png")))
    except (OSError, ValueError):
        return "1"


def render_index_html():
    return INDEX_HTML.replace("{{ICON_VERSION}}", icon_version())


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

    def send_file(self, path):
        try:
            content = path.read_bytes()
        except OSError:
            self.send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return

        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)

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
            self.send_text(render_index_html())
            return
        if path.startswith("/icons/"):
            icon_name = unquote(path.removeprefix("/icons/"))
            icon_path = (ICONS_DIR / icon_name).resolve()
            if ICONS_DIR.resolve() not in icon_path.parents or icon_path.suffix.lower() != ".png":
                self.send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
                return
            self.send_file(icon_path)
            return
        if path == "/api/books":
            self.send_json(load_data())
            return
        if path == "/api/livelib":
            query = parse_qs(urlparse(self.path).query)
            title = query.get("title", [""])[0]
            author = query.get("author", [""])[0]
            self.send_json(fetch_book_info(title, author))
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
        if path == "/api/rating":
            self.rate_book(body)
            return
        if path == "/api/series-count":
            self.set_series_count(body)
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
        duplicate_location = duplicate_book_location(data, book)
        if duplicate_location:
            self.send_json(
                {"error": f"Такая книга уже есть в {duplicate_location}."},
                status=HTTPStatus.CONFLICT,
            )
            return

        book = apply_existing_series_name(data, book)
        if not apply_series_count_from_body(data, book, body):
            self.send_json({"error": "Series count must be a number"}, status=HTTPStatus.BAD_REQUEST)
            return

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

        book = apply_existing_series_name(data, book)
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

    def rate_book(self, body):
        target = body.get("target")
        try:
            index = int(body.get("index", -1))
        except (TypeError, ValueError):
            index = -1

        if target not in VALID_LISTS:
            self.send_json({"error": "Unknown list"}, status=HTTPStatus.BAD_REQUEST)
            return

        data = load_data()
        if index < 0 or index >= len(data[target]):
            self.send_json({"error": "Book not found"}, status=HTTPStatus.NOT_FOUND)
            return

        field = body.get("field")
        if field not in {"rating_penguin", "rating_chick"}:
            self.send_json({"error": "Unknown rating field"}, status=HTTPStatus.BAD_REQUEST)
            return

        data[target][index][field] = normalize_rating(body.get("rating", ""))
        save_data(data)
        self.send_json(data)

    def set_series_count(self, body):
        author = str(body.get("author", "")).strip()
        series = str(body.get("series", "")).strip()
        if not series or series == "Без цикла":
            self.send_json({"error": "Series is required"}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            count = int(str(body.get("count", "") or "0"))
        except ValueError:
            count = 0

        data = load_data()
        key = series_key(author, series)
        data.setdefault("series_counts", {})
        if count > 0:
            data["series_counts"][key] = count
        else:
            data["series_counts"].pop(key, None)

        save_data(data)
        self.send_json(data)


def main():
    lan_ip = get_lan_ip()
    migrate_legacy_data_file()
    restore_status = safe_restore_from_github(DATA_FILE)
    ensure_data_file_schema(backup=restore_status != "failed")
    if restore_status in {"skipped", "missing"}:
        safe_backup_if_due(DATA_FILE)
    server = ThreadingHTTPServer((HOST, PORT), LibraryHandler)
    print("Library server is running.")
    print(f"Open on this computer: http://127.0.0.1:{PORT}")
    print(f"Open on your phone:    http://{lan_ip}:{PORT}")
    print("Keep this window open while using the app.")
    server.serve_forever()


if __name__ == "__main__":
    main()
