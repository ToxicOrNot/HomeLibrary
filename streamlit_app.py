import html
import json
import os
from pathlib import Path
from urllib.parse import urlencode

import streamlit as st

from github_backup import get_last_backup_status, safe_backup_if_due

DATA_DIR = Path(__file__).with_name("data")
DATA_FILE = Path(os.environ.get("DATA_FILE", DATA_DIR / "library_data.json"))
LEGACY_DATA_FILE = Path(__file__).with_name("library_data.json")
VALID_LISTS = {"owned", "wishlist"}


def empty_data():
    return {"owned": [], "wishlist": []}


def normalize_book(item):
    return {
        "title": str(item.get("title", "")).strip(),
        "author": str(item.get("author", "")).strip(),
        "year": str(item.get("year", "")).strip(),
        "series": str(item.get("series", "")).strip(),
        "note": str(item.get("note", "")).strip(),
        "rating": normalize_rating(item.get("rating", "")),
    }


def load_data():
    migrate_legacy_data_file()
    if not DATA_FILE.exists():
        return empty_data()

    try:
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_data()

    data = empty_data()
    for key in VALID_LISTS:
        if isinstance(raw.get(key), list):
            data[key] = [
                book
                for book in (normalize_book(item) for item in raw[key])
                if book["title"]
            ]
    return data


def save_data(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    backup_done = safe_backup_if_due(DATA_FILE, force=True)
    st.session_state["last_backup_status"] = get_last_backup_status()
    st.session_state["last_backup_ok"] = backup_done


def migrate_legacy_data_file():
    if DATA_FILE.exists() or not LEGACY_DATA_FILE.exists():
        return
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(LEGACY_DATA_FILE.read_text(encoding="utf-8"), encoding="utf-8")


def all_books(data):
    return data["owned"] + data["wishlist"]


def unique_sorted(values):
    return sorted(
        {str(value).strip() for value in values if str(value).strip()},
        key=lambda value: value.lower(),
    )


def sorted_groups(items):
    authors = {}
    for index, book in items:
        author = book["author"] or "Автор не указан"
        series = book["series"] or "Без цикла"
        authors.setdefault(author, {}).setdefault(series, []).append((index, book))
    return sorted(authors.items(), key=lambda item: item[0].lower())


def matches_query(book, query):
    if not query:
        return True
    searchable_text = " ".join([book["title"], book["author"], book["series"]])
    return normalize_search(query) in normalize_search(searchable_text)


def normalize_search(value):
    return str(value).lower().replace("ё", "е").strip()


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


def move_between_lists(data, index):
    data["owned"].append(data["wishlist"].pop(index))
    save_data(data)


def reorder_in_series(data, target, index, direction):
    books = data[target]
    book = books[index]
    same_group = [
        item_index
        for item_index, item in enumerate(books)
        if item["author"] == book["author"] and item["series"] == book["series"]
    ]
    position = same_group.index(index)
    new_position = position - 1 if direction == "up" else position + 1
    if 0 <= new_position < len(same_group):
        other_index = same_group[new_position]
        books[index], books[other_index] = books[other_index], books[index]
        save_data(data)


def rerun():
    st.rerun()


def apply_compact_style():
    st.markdown(
        """
        <style>
          [data-testid="stAppViewContainer"] {
            background: #f5f3ef;
          }

          .block-container {
            padding-top: 1rem;
            padding-bottom: 1.4rem;
            max-width: 1180px;
          }

          h1 {
            color: #1f2933;
            font-size: 1.9rem !important;
            margin-bottom: 0.1rem !important;
          }

          h2, h3 {
            margin-top: 0.35rem !important;
          }

          h5 {
            margin: 0.45rem 0 0.2rem !important;
            font-size: 0.95rem !important;
          }

          div[data-testid="stExpander"] {
            border-radius: 8px;
            border-color: #d8dee7;
          }

          div[data-testid="stExpander"] details summary {
            padding-top: 0.45rem;
            padding-bottom: 0.45rem;
          }

          div[data-testid="stVerticalBlock"] {
            gap: 0.28rem;
          }

          div[data-testid="stHorizontalBlock"] {
            gap: 0.35rem;
          }

          div[data-testid="stButton"] > button {
            min-height: 2rem;
            padding: 0.2rem 0.45rem;
            border-radius: 6px;
            font-size: 0.85rem;
          }

          div[data-testid="stTextInput"] input,
          div[data-testid="stSelectbox"] div[data-baseweb="select"] {
            min-height: 2.25rem;
            border-radius: 7px;
          }

          div[data-testid="stTextInput"] label,
          div[data-testid="stSelectbox"] label,
          div[data-testid="stRadio"] label {
            font-size: 0.82rem;
          }

          div[data-testid="stForm"],
          div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #ffffff;
            border-color: #d8dee7;
            border-radius: 8px;
            box-shadow: 0 10px 28px rgba(31, 41, 51, 0.06);
          }

          .app-header {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 0.8rem;
          }

          .app-title {
            color: #1f2933;
            font-size: 1.9rem;
            font-weight: 800;
            line-height: 1.1;
          }

          .app-count {
            color: #48658c;
            font-size: 0.88rem;
            text-align: right;
          }

          .list-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
            margin: 0.15rem 0 0.55rem;
          }

          .list-title strong {
            color: #111827;
            font-size: 1.05rem;
          }

          .list-title span {
            color: #48658c;
            font-size: 0.82rem;
          }

          .author-heading {
            margin: 0.65rem 0 0.35rem;
            padding: 0.45rem 0.6rem;
            border-radius: 7px;
            background: #eef2f7;
            color: #334155;
            font-size: 0.92rem;
            font-weight: 800;
          }

          .series-block {
            margin-left: 0.65rem;
            padding-left: 0.7rem;
            border-left: 2px solid #d8dee7;
          }

          .series-heading {
            color: #475569;
            font-size: 0.88rem;
            font-weight: 800;
            margin: 0.35rem 0 0.2rem;
          }

          .book-actions {
            display: flex;
            flex-direction: row;
            flex-wrap: nowrap;
            gap: 0.35rem;
            align-items: center;
            margin: -0.05rem 0 0.35rem;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
          }

          .book-actions a {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 auto;
            min-width: 2.1rem;
            height: 2rem;
            padding: 0 0.55rem;
            border: 1px solid #d8dee7;
            border-radius: 6px;
            background: #f8fafc;
            color: #1f2933 !important;
            text-decoration: none !important;
            font-weight: 700;
            line-height: 1;
          }

          .book-actions a.danger {
            color: #b42318 !important;
            background: #fff1ef;
            border-color: #f4c7c0;
          }

          .book-actions a.success {
            color: #1f7a4c !important;
            background: #e4f3eb;
            border-color: #b7dfc8;
          }

          hr {
            margin: 0.15rem 0 0.35rem !important;
          }

          @media (max-width: 760px) {
            .block-container {
              padding-left: 0.75rem;
              padding-right: 0.75rem;
            }

            .app-header {
              display: block;
            }

            .app-title {
              font-size: 1.55rem;
            }

            .app-count {
              margin-top: 0.35rem;
              text-align: left;
            }

            .series-block {
              margin-left: 0.35rem;
              padding-left: 0.55rem;
            }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def book_form(data):
    books = all_books(data)
    authors = unique_sorted(book["author"] for book in books)

    with st.form("add_book", clear_on_submit=True):
        cols = st.columns([1.2, 1, 0.5, 1, 1])
        title = cols[0].text_input("Название")

        selected_author = cols[1].selectbox(
            "Автор",
            [""] + authors,
            index=0,
        )
        custom_author = cols[1].text_input(
            "Новый автор",
            placeholder="Новый автор",
            label_visibility="collapsed",
        )
        author = custom_author.strip() or selected_author

        year = cols[2].text_input("Год")

        cycles_source = [
            book["series"]
            for book in books
            if not author.strip() or book["author"] == author.strip()
        ]
        series_options = unique_sorted(cycles_source)
        selected_series = cols[3].selectbox("Цикл", [""] + series_options, index=0)
        custom_series = cols[3].text_input(
            "Новый цикл",
            placeholder="Новый цикл",
            label_visibility="collapsed",
        )
        series = custom_series.strip() or selected_series
        note = cols[4].text_input("Заметка")

        action_cols = st.columns([0.2, 0.18, 0.62])
        add_owned = action_cols[0].form_submit_button("Добавить в библиотеку")
        add_wishlist = action_cols[1].form_submit_button("Добавить в желаемое")

    if add_owned or add_wishlist:
        if not title.strip():
            st.warning("Введите название книги.")
            return
        target = "owned" if add_owned else "wishlist"
        data[target].append(
            normalize_book(
                {
                    "title": title,
                    "author": author,
                    "year": year,
                    "series": series,
                    "note": note,
                    "rating": "",
                }
            )
        )
        save_data(data)
        st.success("Книга добавлена.")
        rerun()


def edit_book_form(data, target, index):
    book = data[target][index]
    with st.expander("Редактирование", expanded=True):
        with st.form(f"edit_{target}_{index}"):
            title = st.text_input("Название", value=book["title"], key=f"title_{target}_{index}")
            cols = st.columns([1, 1, 0.55])
            author = cols[0].text_input("Автор", value=book["author"], key=f"author_{target}_{index}")
            series = cols[1].text_input("Цикл", value=book["series"], key=f"series_{target}_{index}")
            year = cols[2].text_input("Год", value=book["year"], key=f"year_{target}_{index}")
            note = st.text_input("Заметка", value=book["note"], key=f"note_{target}_{index}")
            rating = st.selectbox(
                "Оценка",
                [""] + [str(value) for value in range(1, 11)],
                index=([""] + [str(value) for value in range(1, 11)]).index(book.get("rating", "")),
                key=f"rating_{target}_{index}",
            )
            submitted = st.form_submit_button("Сохранить")
        if submitted:
            if not title.strip():
                st.warning("Введите название книги.")
                return
            data[target][index] = normalize_book(
                {
                    "title": title,
                    "author": author,
                    "series": series,
                    "year": year,
                    "note": note,
                    "rating": rating,
                }
            )
            save_data(data)
            st.success("Книга обновлена.")
            rerun()


def action_url(action, target, index):
    return "?" + urlencode({"action": action, "target": target, "index": index})


def handle_action_params(data):
    action = st.query_params.get("action")
    target = st.query_params.get("target")
    raw_index = st.query_params.get("index")

    if not action or target not in VALID_LISTS or raw_index is None:
        return

    try:
        index = int(raw_index)
    except (TypeError, ValueError):
        st.query_params.clear()
        rerun()
        return

    if index < 0 or index >= len(data[target]):
        st.query_params.clear()
        rerun()
        return

    if action == "up":
        reorder_in_series(data, target, index, "up")
    elif action == "down":
        reorder_in_series(data, target, index, "down")
    elif action == "edit":
        st.session_state["edit"] = (target, index)
    elif action == "move" and target == "wishlist":
        move_between_lists(data, index)
    elif action == "delete":
        del data[target][index]
        save_data(data)

    st.query_params.clear()
    rerun()


def render_book(data, target, index, book):
    meta = " · ".join(part for part in [book["author"], book["year"]] if part)
    with st.container(border=True):
        st.markdown(f"**{book['title']}**")
        if meta:
            st.caption(meta)
        if book["series"]:
            st.caption(f"Цикл: {book['series']}")
        if book["note"]:
            st.write(book["note"])

        rating_options = [""] + [str(value) for value in range(1, 11)]
        current_rating = normalize_rating(book.get("rating", ""))
        selected_rating = st.selectbox(
            "Оценка",
            rating_options,
            index=rating_options.index(current_rating),
            key=f"rating_select_{target}_{index}_{current_rating}",
            label_visibility="collapsed",
            placeholder="Оценка",
        )
        if selected_rating != current_rating:
            data[target][index]["rating"] = selected_rating
            save_data(data)
            rerun()

        move_action = (
            f'<a class="success" href="{action_url("move", target, index)}" title="В библиотеку">✓</a>'
            if target == "wishlist"
            else ""
        )
        st.markdown(
            f"""
            <div class="book-actions">
              <a href="{action_url("up", target, index)}" title="Поднять">↑</a>
              <a href="{action_url("down", target, index)}" title="Опустить">↓</a>
              <a href="{action_url("edit", target, index)}" title="Редактировать">✎</a>
              {move_action}
              <a class="danger" href="{action_url("delete", target, index)}" title="Удалить">×</a>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.get("edit") == (target, index):
            edit_book_form(data, target, index)


def render_list(data, target, title):
    st.markdown(
        f'<div class="list-title"><strong>{html.escape(title)}</strong><span>{len(data[target])} книг</span></div>',
        unsafe_allow_html=True,
    )
    query = st.text_input(
        "Поиск",
        key=f"search_{target}",
        placeholder="Книга, автор или цикл",
        label_visibility="collapsed",
    )

    visible = [
        (index, book)
        for index, book in enumerate(data[target])
        if matches_query(book, query.strip())
    ]
    if not visible:
        st.info("Ничего не найдено.")
        return

    for author, series_groups in sorted_groups(visible):
        total = sum(len(items) for items in series_groups.values())
        st.markdown(
            f'<div class="author-heading">{html.escape(author)} · {total} книги</div>',
            unsafe_allow_html=True,
        )
        for series, items in sorted(series_groups.items(), key=lambda item: item[0].lower()):
            st.markdown(
                f'<div class="series-block"><div class="series-heading">{html.escape(series)} · {len(items)} книги</div></div>',
                unsafe_allow_html=True,
            )
            for index, book in items:
                render_book(data, target, index, book)


def main():
    st.set_page_config(page_title="Домашняя библиотека", layout="wide")
    apply_compact_style()

    data = load_data()
    safe_backup_if_due(DATA_FILE)
    st.session_state.setdefault("last_backup_status", get_last_backup_status())
    st.session_state.setdefault("last_backup_ok", None)
    handle_action_params(data)
    st.markdown(
        f"""
        <div class="app-header">
          <div class="app-title">Домашняя библиотека</div>
          <div class="app-count">В библиотеке: {len(data['owned'])} | В желаемом: {len(data['wishlist'])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    backup_status = st.session_state.get("last_backup_status", "")
    if backup_status:
        if st.session_state.get("last_backup_ok") is False:
            st.warning(backup_status)
        else:
            st.caption(backup_status)

    book_form(data)

    lists = st.columns(2)
    with lists[0]:
        render_list(data, "owned", "Мои книги")
    with lists[1]:
        render_list(data, "wishlist", "Желаемое")


if __name__ == "__main__":
    main()
