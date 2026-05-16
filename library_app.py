import json
import tkinter as tk
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Optional


DATA_FILE = Path(__file__).with_name("library_data.json")


@dataclass
class Book:
    title: str
    author: str
    year: str
    note: str


class LibraryStorage:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, list[Book]]:
        if not self.path.exists():
            return {"owned": [], "wishlist": []}

        try:
            raw_data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            messagebox.showwarning(
                "Ошибка чтения",
                "Не удалось прочитать файл данных. Будет открыт пустой список.",
            )
            return {"owned": [], "wishlist": []}

        return {
            "owned": [Book(**item) for item in raw_data.get("owned", [])],
            "wishlist": [Book(**item) for item in raw_data.get("wishlist", [])],
        }

    def save(self, data: dict[str, list[Book]]) -> None:
        serialized = {
            "owned": [asdict(book) for book in data["owned"]],
            "wishlist": [asdict(book) for book in data["wishlist"]],
        }
        self.path.write_text(
            json.dumps(serialized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class BookForm(ttk.LabelFrame):
    def __init__(self, master: tk.Widget, on_add: Callable) -> None:
        super().__init__(master, text="Новая книга", padding=12)
        self.on_add = on_add
        self.entries: dict[str, ttk.Entry] = {}

        fields = [
            ("title", "Название"),
            ("author", "Автор"),
            ("year", "Год"),
            ("note", "Заметка"),
        ]

        for row, (key, label) in enumerate(fields):
            ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", pady=4)
            entry = ttk.Entry(self, width=36)
            entry.grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=4)
            self.entries[key] = entry

        button_row = ttk.Frame(self)
        button_row.grid(row=len(fields), column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Button(
            button_row,
            text="Добавить в библиотеку",
            command=lambda: self.submit("owned"),
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ttk.Button(
            button_row,
            text="Добавить в желаемое",
            command=lambda: self.submit("wishlist"),
        ).pack(side="left", expand=True, fill="x", padx=(6, 0))

        self.columnconfigure(1, weight=1)
        self.entries["title"].focus()

    def submit(self, target: str) -> None:
        title = self.entries["title"].get().strip()
        author = self.entries["author"].get().strip()
        year = self.entries["year"].get().strip()
        note = self.entries["note"].get().strip()

        if not title:
            messagebox.showinfo("Нужно название", "Введите хотя бы название книги.")
            self.entries["title"].focus()
            return

        self.on_add(target, Book(title=title, author=author, year=year, note=note))
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self.entries["title"].focus()


class BookTable(ttk.LabelFrame):
    def __init__(
        self,
        master: tk.Widget,
        title: str,
        on_delete: Callable,
        on_move: Optional[Callable] = None,
    ) -> None:
        super().__init__(master, text=title, padding=12)
        self.on_delete = on_delete
        self.on_move = on_move

        columns = ("title", "author", "year", "note")
        self.table = ttk.Treeview(self, columns=columns, show="headings", height=10)
        headings = {
            "title": "Название",
            "author": "Автор",
            "year": "Год",
            "note": "Заметка",
        }
        widths = {"title": 220, "author": 160, "year": 70, "note": 240}

        for column in columns:
            self.table.heading(column, text=headings[column])
            self.table.column(column, width=widths[column], minwidth=60, stretch=True)

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        actions = ttk.Frame(self)
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(actions, text="Удалить", command=self.delete_selected).pack(
            side="left", fill="x", expand=True
        )

        if self.on_move:
            ttk.Button(actions, text="Перенести в библиотеку", command=self.move_selected).pack(
                side="left", fill="x", expand=True, padx=(10, 0)
            )

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    def set_books(self, books: list[Book]) -> None:
        self.table.delete(*self.table.get_children())
        for index, book in enumerate(books):
            self.table.insert(
                "",
                tk.END,
                iid=str(index),
                values=(book.title, book.author, book.year, book.note),
            )

    def selected_index(self) -> Optional[int]:
        selected = self.table.selection()
        if not selected:
            messagebox.showinfo("Ничего не выбрано", "Выберите книгу в списке.")
            return None
        return int(selected[0])

    def delete_selected(self) -> None:
        index = self.selected_index()
        if index is not None:
            self.on_delete(index)

    def move_selected(self) -> None:
        index = self.selected_index()
        if index is not None and self.on_move:
            self.on_move(index)


class LibraryApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Домашняя библиотека")
        self.geometry("980x680")
        self.minsize(820, 560)

        self.storage = LibraryStorage(DATA_FILE)
        self.data = self.storage.load()

        self.configure(padx=16, pady=16)
        self.create_widgets()
        self.refresh()

    def create_widgets(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(
            header,
            text="Домашняя библиотека",
            font=("Segoe UI", 18, "bold"),
        ).pack(side="left")
        self.counter_label = ttk.Label(header, text="")
        self.counter_label.pack(side="right")

        self.form = BookForm(self, self.add_book)
        self.form.pack(fill="x", pady=(0, 12))

        tables = ttk.PanedWindow(self, orient="horizontal")
        tables.pack(fill="both", expand=True)

        self.owned_table = BookTable(
            tables,
            "Мои книги",
            on_delete=lambda index: self.delete_book("owned", index),
        )
        self.wishlist_table = BookTable(
            tables,
            "Желаемое",
            on_delete=lambda index: self.delete_book("wishlist", index),
            on_move=self.move_to_owned,
        )

        tables.add(self.owned_table, weight=1)
        tables.add(self.wishlist_table, weight=1)

    def add_book(self, target: str, book: Book) -> None:
        self.data[target].append(book)
        self.persist_and_refresh()

    def delete_book(self, target: str, index: int) -> None:
        book = self.data[target][index]
        confirmed = messagebox.askyesno(
            "Удалить книгу",
            f"Удалить «{book.title}»?",
        )
        if confirmed:
            del self.data[target][index]
            self.persist_and_refresh()

    def move_to_owned(self, index: int) -> None:
        book = self.data["wishlist"].pop(index)
        self.data["owned"].append(book)
        self.persist_and_refresh()

    def persist_and_refresh(self) -> None:
        self.storage.save(self.data)
        self.refresh()

    def refresh(self) -> None:
        self.owned_table.set_books(self.data["owned"])
        self.wishlist_table.set_books(self.data["wishlist"])
        self.counter_label.config(
            text=(
                f"В библиотеке: {len(self.data['owned'])} | "
                f"В желаемом: {len(self.data['wishlist'])}"
            )
        )


if __name__ == "__main__":
    app = LibraryApp()
    app.mainloop()
