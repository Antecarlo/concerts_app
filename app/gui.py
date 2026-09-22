import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
from typing import List, Dict, Tuple, Optional

from app.database import (
    init_db, add_concert, set_calendar_event_id,
    get_concerts, get_concerts_without_calendar_event
)
from app.pdf_parser import parse_pdf
from app.calendar_sync import create_calendar_event
from datetime import datetime


class ConcertDiaryApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("My Concert Diary")
        self.geometry("900x700")
        self.minsize(800, 600)

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        init_db()

        self.pending_concerts: List[Dict] = []
        self.saved_concerts: List[tuple] = []

        self._create_widgets()
        self._refresh_saved_list()

    # ── Widget construction ──────────────────────────────────────────────

    def _create_widgets(self):
        main_frame = ctk.CTkFrame(self, corner_radius=0)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            main_frame,
            text="My Concert Diary",
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=(0, 20))

        # ── PDF import section ──
        import_frame = ctk.CTkFrame(main_frame)
        import_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            import_frame,
            text="Import from PDF",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(15, 10))

        # Drag & drop zone
        self.drop_zone = ctk.CTkFrame(import_frame, height=90,
                                       border_width=2,
                                       border_color=("gray70", "gray30"))
        self.drop_zone.pack(fill="x", padx=20, pady=(0, 10))
        self.drop_zone.pack_propagate(False)

        self.drop_label = ctk.CTkLabel(
            self.drop_zone,
            text="📄 Drag & drop PDF files here\nor click to browse",
            font=ctk.CTkFont(size=14),
            text_color=("gray50", "gray50")
        )
        self.drop_label.pack(expand=True)

        self.drop_zone.bind("<Button-1>", lambda e: self._browse_pdf())
        self.drop_label.bind("<Button-1>", lambda e: self._browse_pdf())

        # Import action buttons
        btn_frame = ctk.CTkFrame(import_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.btn_save_imported = ctk.CTkButton(
            btn_frame, text="Save Imported", height=35, state="disabled",
            command=self._save_imported_concerts
        )
        self.btn_save_imported.pack(side="left", padx=5)

        self.btn_clear_import = ctk.CTkButton(
            btn_frame, text="Clear Import", height=35,
            fg_color="transparent", border_width=1,
            text_color=("gray30", "gray70"), state="disabled",
            command=self._clear_import
        )
        self.btn_clear_import.pack(side="left", padx=5)

        # ── Review table ──
        review_frame = ctk.CTkFrame(main_frame)
        review_frame.pack(fill="both", expand=True, pady=(0, 15))

        review_header = ctk.CTkFrame(review_frame, fg_color="transparent")
        review_header.pack(fill="x", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            review_header, text="Concerts to Review",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left")

        self.review_count = ctk.CTkLabel(
            review_header, text="(0 concerts)",
            font=ctk.CTkFont(size=12), text_color=("gray50", "gray50")
        )
        self.review_count.pack(side="left", padx=10)

        self.review_scroll = ctk.CTkScrollableFrame(review_frame, height=180)
        self.review_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self._build_review_header()

        # ── Saved concerts + sync ──
        saved_frame = ctk.CTkFrame(main_frame)
        saved_frame.pack(fill="both", expand=True)

        saved_header = ctk.CTkFrame(saved_frame, fg_color="transparent")
        saved_header.pack(fill="x", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            saved_header, text="Saved Concerts",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left")

        self.saved_count = ctk.CTkLabel(
            saved_header, text="(0 concerts)",
            font=ctk.CTkFont(size=12), text_color=("gray50", "gray50")
        )
        self.saved_count.pack(side="left", padx=10)

        self.btn_sync = ctk.CTkButton(
            saved_header, text="☁ Sync to Google Calendar",
            command=self._sync_to_calendar, height=35, width=180
        )
        self.btn_sync.pack(side="right")

        self.saved_scroll = ctk.CTkScrollableFrame(saved_frame, height=180)
        self.saved_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self._build_saved_header()

        # Status bar
        self.status = ctk.CTkLabel(
            main_frame, text="Ready", anchor="w",
            font=ctk.CTkFont(size=11), text_color=("gray50", "gray50")
        )
        self.status.pack(fill="x", padx=15, pady=(5, 0))

    # ── Table headers ────────────────────────────────────────────────────

    def _build_review_header(self):
        for w in self.review_scroll.winfo_children():
            w.destroy()
        headers = ["Date", "Venue", "Notes", "Actions"]
        widths = [100, 200, 350, 120]
        for i, (h, w_) in enumerate(zip(headers, widths)):
            ctk.CTkLabel(self.review_scroll, text=h,
                         font=ctk.CTkFont(weight="bold"),
                         width=w_, anchor="w") \
                .grid(row=0, column=i, padx=5, pady=5, sticky="w")
        self.review_scroll.grid_columnconfigure(2, weight=1)

    def _build_saved_header(self):
        for w in self.saved_scroll.winfo_children():
            w.destroy()
        headers = ["Date", "Venue", "Notes", "Calendar", "Actions"]
        widths = [100, 200, 300, 90, 120]
        for i, (h, w_) in enumerate(zip(headers, widths)):
            ctk.CTkLabel(self.saved_scroll, text=h,
                         font=ctk.CTkFont(weight="bold"),
                         width=w_, anchor="w") \
                .grid(row=0, column=i, padx=5, pady=5, sticky="w")
        self.saved_scroll.grid_columnconfigure(2, weight=1)

    # ── Populate review table ────────────────────────────────────────────

    def _populate_review_table(self):
        for w in self.review_scroll.winfo_children():
            row = w.grid_info().get("row", 0)
            if row > 0:
                w.destroy()

        for r, concert in enumerate(self.pending_concerts, start=1):
            date_e = ctk.CTkEntry(self.review_scroll, width=100)
            date_e.insert(0, concert.get("date", ""))
            date_e.grid(row=r, column=0, padx=5, pady=3, sticky="w")

            loc_e = ctk.CTkEntry(self.review_scroll, width=200)
            loc_e.insert(0, concert.get("location", ""))
            loc_e.grid(row=r, column=1, padx=5, pady=3, sticky="w")

            notes_e = ctk.CTkEntry(self.review_scroll, width=350)
            notes_e.insert(0, concert.get("notes", ""))
            notes_e.grid(row=r, column=2, padx=5, pady=3, sticky="ew")

            btn_del = ctk.CTkButton(
                self.review_scroll, text="🗑", width=30, height=28,
                command=lambda idx=r-1: self._delete_review_row(idx)
            )
            btn_del.grid(row=r, column=3, padx=5, pady=3)

            concert["_widgets"] = (date_e, loc_e, notes_e)

        self.review_count.configure(text=f"({len(self.pending_concerts)} concerts)")
        enabled = len(self.pending_concerts) > 0
        self.btn_save_imported.configure(state="normal" if enabled else "disabled")
        self.btn_clear_import.configure(state="normal" if enabled else "disabled")

    # ── Populate saved table ─────────────────────────────────────────────

    def _populate_saved_table(self):
        for w in self.saved_scroll.winfo_children():
            if w.grid_info().get("row", 0) > 0:
                w.destroy()

        for r, c in enumerate(self.saved_concerts, start=1):
            cid, date, loc, notes, cal_id, source = c

            ctk.CTkLabel(self.saved_scroll, text=date, width=100,
                         anchor="w") \
                .grid(row=r, column=0, padx=5, pady=3, sticky="w")

            ctk.CTkLabel(self.saved_scroll, text=loc, width=200,
                         anchor="w") \
                .grid(row=r, column=1, padx=5, pady=3, sticky="w")

            ctk.CTkLabel(self.saved_scroll, text=notes or "-",
                         width=300, anchor="w") \
                .grid(row=r, column=2, padx=5, pady=3, sticky="ew")

            cal_txt = "✓ Synced" if cal_id else "✗ Not synced"
            cal_clr = "green" if cal_id else "orange"
            ctk.CTkLabel(self.saved_scroll, text=cal_txt, width=90,
                         anchor="w", text_color=cal_clr) \
                .grid(row=r, column=3, padx=5, pady=3, sticky="w")

            # Action buttons
            action_f = ctk.CTkFrame(self.saved_scroll, fg_color="transparent")
            action_f.grid(row=r, column=4, padx=5, pady=3)

            if not cal_id:
                ctk.CTkButton(
                    action_f, text="Sync", width=55, height=28,
                    command=lambda _id=cid, d=date, l=loc, n=notes:
                        self._sync_single(_id, d, l, n)
                ).pack(side="left", padx=2)

        self.saved_count.configure(text=f"({len(self.saved_concerts)} concerts)")

    # ── Handlers ─────────────────────────────────────────────────────────

    def _browse_pdf(self):
        files = filedialog.askopenfilenames(
            title="Select PDF files",
            filetypes=[("PDF files", "*.pdf")]
        )
        if files:
            self._process_pdfs(list(files))

    def _process_pdfs(self, paths: List[str]):
        self.status.configure(text="Processing PDFs…")
        self.btn_save_imported.configure(state="disabled")
        self.btn_clear_import.configure(state="disabled")

        def worker():
            all_c = []
            errors = []
            for p in paths:
                try:
                    all_c.extend(parse_pdf(p))
                except Exception as e:
                    errors.append(f"{os.path.basename(p)}: {e}")
            self.after(0, lambda: self._on_pdfs_done(all_c, errors))

        threading.Thread(target=worker, daemon=True).start()

    def _on_pdfs_done(self, concerts: List[Dict], errors: List[str]):
        self.pending_concerts = concerts
        self._populate_review_table()

        if errors:
            msg = "Errors parsing the following files:\n\n" + "\n".join(errors)
            messagebox.showerror("PDF parse errors", msg)

        if not concerts and not errors:
            messagebox.showinfo("No data found", "No concert information could be extracted from the PDF(s).")

        self.status.configure(
            text=f"Parsed {len(concerts)} concert(s) from PDF. Edit & save."
        )

    def _save_imported_concerts(self):
        saved = 0
        for concert in self.pending_concerts:
            widgets = concert.get("_widgets")
            if not widgets:
                continue
            date_e, loc_e, notes_e = widgets
            date = date_e.get().strip()
            loc = loc_e.get().strip()
            notes = notes_e.get().strip()

            if not date or not loc:
                continue
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                continue

            add_concert(date, loc, notes, concert.get("source_file", ""))
            saved += 1

        self.pending_concerts.clear()
        self._populate_review_table()
        self._refresh_saved_list()
        self.status.configure(text=f"Saved {saved} concert(s).")

    def _clear_import(self):
        self.pending_concerts.clear()
        self._populate_review_table()
        self.status.configure(text="Import cleared.")

    def _delete_review_row(self, idx: int):
        if 0 <= idx < len(self.pending_concerts):
            del self.pending_concerts[idx]
            self._populate_review_table()

    def _refresh_saved_list(self):
        self.saved_concerts = get_concerts()
        self._populate_saved_table()

    def _sync_single(self, cid: int, date: str, loc: str, notes: str):
        self._run_sync([(cid, date, loc, notes)])

    def _sync_to_calendar(self):
        unsynced = get_concerts_without_calendar_event()
        if not unsynced:
            messagebox.showinfo("Sync", "All concerts are already synced.")
            return

        dialog = SyncDialog(self, unsynced)
        self.wait_window(dialog)
        if dialog.confirmed:
            selected = dialog.get_selected()
            if selected:
                self._run_sync(selected)

    def _run_sync(self, concerts: List[tuple]):
        self.btn_sync.configure(state="disabled", text="Syncing…")
        self.status.configure(text="Syncing to Google Calendar…")

        def worker():
            results = []
            for c in concerts:
                cid, date, loc, notes = c[0], c[1], c[2], c[3]
                try:
                    event_id = create_calendar_event(date, loc, notes)
                    set_calendar_event_id(cid, event_id)
                    results.append((cid, True, ""))
                except Exception as e:
                    results.append((cid, False, str(e)))
            self.after(0, lambda: self._on_sync_done(results))

        threading.Thread(target=worker, daemon=True).start()

    def _on_sync_done(self, results: List[tuple]):
        ok = sum(1 for r in results if r[1])
        failed = [(cid, err) for cid, ok_, err in results if not ok_]

        self.btn_sync.configure(state="normal", text="☁ Sync to Google Calendar")
        self._refresh_saved_list()

        if failed:
            msg = "\n".join(f"ID {cid}: {err}" for cid, err in failed)
            messagebox.showerror("Sync errors", f"Synced {ok}.\nErrors:\n{msg}")
            self.status.configure(text=f"Sync done with {len(failed)} error(s).")
        else:
            messagebox.showinfo("Sync complete",
                                f"Successfully synced {ok} concert(s) to Calendar!")
            self.status.configure(text=f"Synced {ok} concert(s).")


# ── Sync confirmation dialog ──────────────────────────────────────────

class SyncDialog(ctk.CTkToplevel):
    def __init__(self, parent, concerts: List[tuple]):
        super().__init__(parent)
        self.title("Confirm sync to Google Calendar")
        self.geometry("550x400")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.confirmed = False
        self._concerts = concerts
        self._pairs: List[Tuple[int, tk.BooleanVar]] = []

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        ctk.CTkLabel(
            self, text="Select concerts to sync:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(20, 10))

        scroll = ctk.CTkScrollableFrame(self, height=240)
        scroll.pack(fill="both", expand=True, padx=20, pady=10)

        for c in concerts:
            cid, dt, loc, notes = c[:4]
            label = f"{dt}  |  {loc[:40]}  |  {notes[:40] if notes else '-'}"
            var = tk.BooleanVar(value=True)
            cb = ctk.CTkCheckBox(scroll, text=label, variable=var,
                                 font=ctk.CTkFont(size=12))
            cb.pack(anchor="w", pady=4, padx=10)
            self._pairs.append((cid, var))

        btn_f = ctk.CTkFrame(self, fg_color="transparent")
        btn_f.pack(fill="x", padx=20, pady=20)

        ctk.CTkButton(btn_f, text="Cancel", width=100,
                      fg_color="transparent", border_width=1,
                      command=self.destroy).pack(side="right", padx=10)

        ctk.CTkButton(btn_f, text="Sync Selected", width=120,
                      command=self._confirm).pack(side="right", padx=10)

    def _confirm(self):
        self.confirmed = True
        self.destroy()

    def get_selected(self) -> List[tuple]:
        return [c for c in self._concerts
                if any(c[0] == cid and var.get() for cid, var in self._pairs)]


def main():
    app = ConcertDiaryApp()
    app.mainloop()


if __name__ == "__main__":
    main()