import html
import json
import os
from pathlib import Path

import streamlit as st


DATA_FILE = Path(os.environ.get("DATA_FILE", Path(__file__).with_name("library_data.json")))
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
    }


def load_data():
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
    DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


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
    haystack = " ".join(
        [book["title"], book["author"], book["year"], book["series"], book["note"]]
    ).lower()
    return query.lower() in haystack


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
          .block-container {
            padding-top: 1.2rem;
            padding-bottom: 1.4rem;
            max-width: 1180px;
          }

          h1 {
            font-size: 1.75rem !important;
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
            gap: 0.35rem;
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
          }

          div[data-testid="stTextInput"] label,
          div[data-testid="stSelectbox"] label,
          div[data-testid="stRadio"] label {
            font-size: 0.82rem;
          }

          .book-card {
            border: 1px solid #d8dee7;
            border-radius: 8px;
            padding: 0.55rem 0.65rem;
            background: #ffffff;
            margin: 0.25rem 0;
          }

          .book-title {
            font-weight: 700;
            line-height: 1.25;
            margin-bottom: 0.1rem;
          }

          .book-meta {
            color: #64748b;
            font-size: 0.82rem;
            line-height: 1.25;
          }

          .book-note {
            color: #475569;
            font-size: 0.86rem;
            margin-top: 0.25rem;
          }

          hr {
            margin: 0.25rem 0 0.45rem !important;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def book_form(data):
    books = all_books(data)
    authors = unique_sorted(book["author"] for book in books)

    with st.expander("Добавить книгу", expanded=False):
        with st.form("add_book", clear_on_submit=True):
            title = st.text_input("Название")

            author_cols = st.columns(2)
            selected_author = author_cols[0].selectbox(
                "Автор из списка",
                [""] + authors,
                index=0,
            )
            author = author_cols[1].text_input("Автор", value=selected_author)

            cycles_source = [
                book["series"]
                for book in books
                if not author.strip() or book["author"] == author.strip()
            ]
            series_options = unique_sorted(cycles_source)

            detail_cols = st.columns([1, 1, 0.55])
            selected_series = detail_cols[0].selectbox(
                "Цикл из списка",
                [""] + series_options,
                index=0,
            )
            series = detail_cols[1].text_input("Цикл", value=selected_series)
            year = detail_cols[2].text_input("Год")
            note = st.text_input("Заметка")
            target_label = st.radio(
                "Куда добавить",
                ["Библиотека", "Желаемое"],
                horizontal=True,
            )
            submitted = st.form_submit_button("Добавить")

    if submitted:
        if not title.strip():
            st.warning("Введите название книги.")
            return
        target = "owned" if target_label == "Библиотека" else "wishlist"
        data[target].append(
            normalize_book(
                {
                    "title": title,
                    "author": author,
                    "year": year,
                    "series": series,
                    "note": note,
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
                }
            )
            save_data(data)
            st.success("Книга обновлена.")
            rerun()


def render_book(data, target, index, book):
    title = html.escape(book["title"])
    meta = " · ".join(part for part in [book["author"], book["year"]] if part)
    note = f"<div class='book-note'>{html.escape(book['note'])}</div>" if book["note"] else ""
    meta_html = f"<div class='book-meta'>{html.escape(meta)}</div>" if meta else ""
    st.markdown(
        f"""
        <div class="book-card">
          <div class="book-title">{title}</div>
          {meta_html}
          {note}
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns([0.55, 0.55, 0.75, 0.85, 0.65, 5])
    if cols[0].button("↑", key=f"up_{target}_{index}", help="Поднять"):
        reorder_in_series(data, target, index, "up")
        rerun()
    if cols[1].button("↓", key=f"down_{target}_{index}", help="Опустить"):
        reorder_in_series(data, target, index, "down")
        rerun()
    if cols[2].button("✎", key=f"edit_btn_{target}_{index}", help="Редактировать"):
        st.session_state["edit"] = (target, index)
        rerun()
    if target == "wishlist" and cols[3].button("✓", key=f"move_{index}", help="В библиотеку"):
        move_between_lists(data, index)
        rerun()
    if cols[4].button("×", key=f"delete_{target}_{index}", help="Удалить"):
        del data[target][index]
        save_data(data)
        rerun()

    if st.session_state.get("edit") == (target, index):
        edit_book_form(data, target, index)


def render_list(data, target, title):
    top_cols = st.columns([1, 1.1, 0.8])
    top_cols[0].subheader(f"{title}: {len(data[target])}")
    query = top_cols[1].text_input("Поиск", key=f"search_{target}", label_visibility="collapsed")
    view = top_cols[2].selectbox(
        "Вид",
        ["Автор → цикл", "Обычный список", "По авторам", "По циклам"],
        key=f"view_{target}",
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

    if view == "Обычный список":
        visible = sorted(
            visible,
            key=lambda item: (
                item[1]["author"].lower(),
                item[1]["series"].lower(),
                item[1]["title"].lower(),
            ),
        )
        for index, book in visible:
            render_book(data, target, index, book)
            st.divider()
        return

    if view == "По авторам":
        groups = {}
        for index, book in visible:
            groups.setdefault(book["author"] or "Автор не указан", []).append((index, book))
        for author in sorted(groups, key=str.lower):
            with st.expander(f"{author} · {len(groups[author])}", expanded=True):
                for index, book in groups[author]:
                    render_book(data, target, index, book)
                    st.divider()
        return

    if view == "По циклам":
        groups = {}
        for index, book in visible:
            groups.setdefault(book["series"] or "Без цикла", []).append((index, book))
        for series in sorted(groups, key=str.lower):
            with st.expander(f"{series} · {len(groups[series])}", expanded=True):
                for index, book in groups[series]:
                    render_book(data, target, index, book)
                    st.divider()
        return

    for author, series_groups in sorted_groups(visible):
        with st.expander(f"{author}", expanded=True):
            for series, items in sorted(series_groups.items(), key=lambda item: item[0].lower()):
                st.markdown(f"##### {series}")
                for index, book in items:
                    render_book(data, target, index, book)
                    st.divider()


def main():
    st.set_page_config(page_title="Домашняя библиотека", layout="wide")
    apply_compact_style()
    st.title("Домашняя библиотека")

    data = load_data()
    st.caption(f"В библиотеке: {len(data['owned'])} | В желаемом: {len(data['wishlist'])}")

    book_form(data)

    owned_tab, wishlist_tab = st.tabs(["Мои книги", "Желаемое"])
    with owned_tab:
        render_list(data, "owned", "Мои книги")
    with wishlist_tab:
        render_list(data, "wishlist", "Желаемое")


if __name__ == "__main__":
    main()
