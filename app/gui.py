import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
from typing import List, Dict, Tuple

from app.database import (
    init_db, add_concert, set_calendar_event_id,
    get_concerts, get_concerts_without_calendar_event, update_concert_color
)
from app.pdf_parser import parse_pdf, _add_hours
from app.calendar_sync import create_calendar_event, upsert_calendar_event
from datetime import datetime


EVENT_COLORS: Dict[str, str] = {
    "": "Default",
    "1": "Lavender",
    "2": "Sage",
    "3": "Grape",
    "4": "Flamingo",
    "5": "Banana",
    "6": "Tangerine",
    "7": "Peacock",
    "8": "Graphite",
    "9": "Blueberry",
    "10": "Basil",
    "11": "Tomato",
}

EVENT_COLOR_HEX: Dict[str, str] = {
    "1": "#7986cb",
    "2": "#33b679",
    "3": "#8e24aa",
    "4": "#e67c73",
    "5": "#f6c026",
    "6": "#f5511d",
    "7": "#039be5",
    "8": "#616161",
    "9": "#3f51b5",
    "10": "#0b8043",
    "11": "#d81b60",
}


class ConcertDiaryApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("My Concert Diary")
        self.geometry("1000x850")
        self.minsize(900, 750)

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        init_db()

        self.pending_concerts: List[Dict] = []
        self.saved_concerts: List[tuple] = []

        self._create_widgets()
        self._refresh_saved_list()

    def _create_widgets(self):
        main_frame = ctk.CTkFrame(self, corner_radius=0)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            main_frame,
            text="My Concert Diary",
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=(0, 20))

        # ── Import frame ──
        import_frame = ctk.CTkFrame(main_frame)
        import_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            import_frame,
            text="Import from PDF",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(15, 10))

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

        # ── Review frame ──
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

        self.review_scroll = ctk.CTkScrollableFrame(review_frame, height=160)
        self.review_scroll.pack(fill="both", expand=False, padx=15, pady=(0, 15))
        self._build_review_header()

        # ── Saved frame ──
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

        self.saved_scroll = ctk.CTkScrollableFrame(saved_frame, height=180)
        self.saved_scroll.pack(fill="x", expand=False, padx=15, pady=(0, 5))
        self._build_saved_header()

        # Sync button BELOW the saved table
        sync_frame = ctk.CTkFrame(saved_frame, fg_color="transparent")
        sync_frame.pack(fill="x", padx=15, pady=(5, 15))

        self.btn_sync = ctk.CTkButton(
            sync_frame, text="☁ Sync to Google Calendar",
            command=self._sync_to_calendar, height=35, width=200
        )
        self.btn_sync.pack(side="right")

        # ── Status bar ──
        self.status = ctk.CTkLabel(
            main_frame, text="Ready", anchor="w",
            font=ctk.CTkFont(size=11), text_color=("gray50", "gray50")
        )
        self.status.pack(fill="x", padx=15, pady=(5, 0))

    def _build_review_header(self):
        for w in self.review_scroll.winfo_children():
            w.destroy()
        headers = ["Date", "Start", "End", "Venue", "Notes", "Actions"]
        widths = [100, 70, 70, 180, 350, 80]
        for i, (h, w_) in enumerate(zip(headers, widths)):
            ctk.CTkLabel(self.review_scroll, text=h,
                         font=ctk.CTkFont(weight="bold"),
                         width=w_, anchor="w") \
                .grid(row=0, column=i, padx=5, pady=5, sticky="w")
        self.review_scroll.grid_columnconfigure(4, weight=1)

    def _build_saved_header(self):
        for w in self.saved_scroll.winfo_children():
            w.destroy()
        headers = ["Date", "Time", "Venue", "Notes", "Color", "Calendar", "Actions"]
        widths = [100, 80, 160, 260, 80, 80, 100]
        for i, (h, w_) in enumerate(zip(headers, widths)):
            ctk.CTkLabel(self.saved_scroll, text=h,
                         font=ctk.CTkFont(weight="bold"),
                         width=w_, anchor="w") \
                .grid(row=0, column=i, padx=5, pady=5, sticky="w")
        self.saved_scroll.grid_columnconfigure(3, weight=1)

    def _populate_review_table(self):
        for w in self.review_scroll.winfo_children():
            row = w.grid_info().get("row", 0)
            if row > 0:
                w.destroy()

        for r, concert in enumerate(self.pending_concerts, start=1):
            date_e = ctk.CTkEntry(self.review_scroll, width=100)
            date_e.insert(0, concert.get("date", ""))
            date_e.grid(row=r, column=0, padx=5, pady=3, sticky="w")

            start_e = ctk.CTkEntry(self.review_scroll, width=70)
            start_e.insert(0, concert.get("start_time", ""))
            start_e.grid(row=r, column=1, padx=5, pady=3, sticky="w")

            end_e = ctk.CTkEntry(self.review_scroll, width=70)
            end_e.insert(0, concert.get("end_time", ""))
            end_e.grid(row=r, column=2, padx=5, pady=3, sticky="w")

            loc_e = ctk.CTkEntry(self.review_scroll, width=180)
            loc_e.insert(0, concert.get("location", ""))
            loc_e.grid(row=r, column=3, padx=5, pady=3, sticky="w")

            notes_e = ctk.CTkEntry(self.review_scroll, width=350)
            notes_e.insert(0, concert.get("notes", ""))
            notes_e.grid(row=r, column=4, padx=5, pady=3, sticky="ew")

            btn_del = ctk.CTkButton(
                self.review_scroll, text="🗑", width=30, height=28,
                command=lambda idx=r-1: self._delete_review_row(idx)
            )
            btn_del.grid(row=r, column=5, padx=5, pady=3)

            concert["_widgets"] = (date_e, start_e, end_e, loc_e, notes_e)

        self.review_count.configure(text=f"({len(self.pending_concerts)} concerts)")
        enabled = len(self.pending_concerts) > 0
        self.btn_save_imported.configure(state="normal" if enabled else "disabled")
        self.btn_clear_import.configure(state="normal" if enabled else "disabled")

    def _populate_saved_table(self):
        for w in self.saved_scroll.winfo_children():
            if w.grid_info().get("row", 0) > 0:
                w.destroy()

        for r, c in enumerate(self.saved_concerts, start=1):
            # row = (id, date, location, notes, cal_id, source, start_time, end_time, color)
            cid, date, loc, notes, cal_id, source, start_time, end_time, color = c

            time_str = f"{start_time} – {end_time}" if start_time and end_time else "All day"
            color_name = EVENT_COLORS.get(color, "Default")
            color_hex = EVENT_COLOR_HEX.get(color, "")

            ctk.CTkLabel(self.saved_scroll, text=date, width=100, anchor="w") \
                .grid(row=r, column=0, padx=5, pady=3, sticky="w")

            ctk.CTkLabel(self.saved_scroll, text=time_str, width=80, anchor="w") \
                .grid(row=r, column=1, padx=5, pady=3, sticky="w")

            ctk.CTkLabel(self.saved_scroll, text=loc, width=160, anchor="w") \
                .grid(row=r, column=2, padx=5, pady=3, sticky="w")

            ctk.CTkLabel(self.saved_scroll, text=notes or "-", width=260, anchor="w") \
                .grid(row=r, column=3, padx=5, pady=3, sticky="ew")

            if color_hex:
                color_lbl = ctk.CTkLabel(
                    self.saved_scroll, text=color_name, width=80,
                    anchor="w", text_color=color_hex,
                    font=ctk.CTkFont(weight="bold")
                )
            else:
                color_lbl = ctk.CTkLabel(
                    self.saved_scroll, text=color_name, width=80, anchor="w"
                )
            color_lbl.grid(row=r, column=4, padx=5, pady=3, sticky="w")

            cal_txt = "✓ Synced" if cal_id else "✗ Not synced"
            cal_clr = "green" if cal_id else "orange"
            ctk.CTkLabel(self.saved_scroll, text=cal_txt, width=80,
                         anchor="w", text_color=cal_clr) \
                .grid(row=r, column=5, padx=5, pady=3, sticky="w")

            action_f = ctk.CTkFrame(self.saved_scroll, fg_color="transparent")
            action_f.grid(row=r, column=6, padx=5, pady=3)

            btn_text = "Re-sync" if cal_id else "Sync"
            ctk.CTkButton(
                action_f, text=btn_text, width=65, height=28,
                command=lambda _id=cid, d=date, l=loc, n=notes,
                               st=start_time, et=end_time, clr=color, ev=cal_id or "":
                    self._sync_single(_id, d, l, n, st, et, clr, ev)
            ).pack(side="left", padx=2)

            ctk.CTkButton(
                action_f, text="Edit", width=45, height=28,
                command=lambda _id=cid, d=date, l=loc, n=notes,
                               st=start_time, et=end_time, clr=color:
                    self._edit_concert(_id, d, l, n, st, et, clr)
            ).pack(side="left", padx=2)

        self.saved_count.configure(text=f"({len(self.saved_concerts)} concerts)")

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
            date_e, start_e, end_e, loc_e, notes_e = widgets
            date = date_e.get().strip()
            start_t = start_e.get().strip()
            end_t = end_e.get().strip()
            loc = loc_e.get().strip()
            notes = notes_e.get().strip()

            if not date or not loc:
                continue
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                continue

            # Validate time format if provided
            if start_t:
                try:
                    datetime.strptime(start_t, "%H:%M")
                except ValueError:
                    continue
            if end_t:
                try:
                    datetime.strptime(end_t, "%H:%M")
                except ValueError:
                    continue

            add_concert(date, loc, notes, concert.get("source_file", ""),
                        start_time=start_t, end_time=end_t)
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

    def _sync_single(self, cid: int, date: str, loc: str, notes: str,
                     start_time: str = "", end_time: str = "", color: str = "",
                     event_id: str = ""):
        concert_tuple = (cid, date, loc, notes, event_id, "", start_time, end_time, color)
        dialog = SyncDialog(self, [concert_tuple], single=True)
        self.wait_window(dialog)
        if dialog.confirmed:
            selected = dialog.get_selected()
            if selected:
                self._run_sync(selected, dialog.selected_color)

    def _sync_to_calendar(self):
        all_concerts = get_concerts()
        if not all_concerts:
            messagebox.showinfo("Sync", "No concerts to sync.")
            return

        dialog = SyncDialog(self, all_concerts, single=False)
        self.wait_window(dialog)
        if dialog.confirmed:
            selected = dialog.get_selected()
            if selected:
                self._run_sync(selected, dialog.selected_color)

    def _edit_concert(self, cid: int, date: str, loc: str, notes: str,
                      start_time: str, end_time: str, color: str):
        """Open a dialog to edit a saved concert's details."""
        dialog = EditConcertDialog(self, cid, date, loc, notes, start_time, end_time, color)
        self.wait_window(dialog)
        if dialog.saved:
            self._refresh_saved_list()

    def _run_sync(self, concerts: List[tuple], sync_color: str = ""):
        self.btn_sync.configure(state="disabled", text="Syncing…")
        self.status.configure(text="Syncing to Google Calendar…")

        def worker():
            results = []
            created = 0
            updated = 0
            for c in concerts:
                cid = c[0]
                date = c[1]
                loc = c[2]
                notes = c[3]
                event_id = c[4] if len(c) > 4 else ""
                start_time = c[6] if len(c) > 6 else ""
                end_time = c[7] if len(c) > 7 else ""
                user_color = c[8] if len(c) > 8 else ""
                color = sync_color if sync_color else user_color
                try:
                    new_event_id = upsert_calendar_event(
                        event_id, date, loc, notes, start_time, end_time, color
                    )
                    set_calendar_event_id(cid, new_event_id)
                    if color:
                        update_concert_color(cid, color)
                    if event_id:
                        updated += 1
                    else:
                        created += 1
                    results.append((cid, True, ""))
                except Exception as e:
                    results.append((cid, False, str(e)))
            self.after(0, lambda: self._on_sync_done(results, created, updated))

        threading.Thread(target=worker, daemon=True).start()

    def _on_sync_done(self, results: List[tuple], created: int = 0, updated: int = 0):
        ok = sum(1 for r in results if r[1])
        failed = [(cid, err) for cid, ok_, err in results if not ok_]

        self.btn_sync.configure(state="normal", text="☁ Sync to Google Calendar")
        self._refresh_saved_list()

        if failed:
            msg = "\n".join(f"ID {cid}: {err}" for cid, err in failed)
            summary = []
            if created:
                summary.append(f"{created} created")
            if updated:
                summary.append(f"{updated} updated")
            summary_str = f" ({', '.join(summary)})" if summary else ""
            messagebox.showerror("Sync errors", f"Done{summary_str}. Errors:\n{msg}")
            self.status.configure(text=f"Sync done with {len(failed)} error(s).")
        else:
            parts = []
            if created:
                parts.append(f"{created} created")
            if updated:
                parts.append(f"{updated} updated")
            msg = f"Successfully synced {ok} concert(s) to Calendar!"
            if parts:
                msg += f"\n({' + '.join(parts)})"
            messagebox.showinfo("Sync complete", msg)
            self.status.configure(text=f"Synced {ok} concert(s).")


class SyncDialog(ctk.CTkToplevel):
    def __init__(self, parent, concerts: List[tuple], single: bool = False):
        super().__init__(parent)
        self.title("Sync to Google Calendar")
        self.geometry("600x500")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.confirmed = False
        self.selected_color = ""
        self._concerts = concerts
        self._pairs: List[Tuple[int, tk.BooleanVar]] = []

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        ctk.CTkLabel(
            self, text="Select concerts to sync:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(20, 10))

        # Color selector
        color_frame = ctk.CTkFrame(self, fg_color="transparent")
        color_frame.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(color_frame, text="Event color:", font=ctk.CTkFont(size=12)) \
            .pack(side="left", padx=(0, 10))

        self.color_var = tk.StringVar(value="")
        color_options = [f"{v} ({k})" if k else v for k, v in EVENT_COLORS.items()]
        self.color_map = {f"{v} ({k})" if k else v: k for k, v in EVENT_COLORS.items()}
        self.color_menu = ctk.CTkOptionMenu(
            color_frame, values=color_options, variable=self.color_var, width=180
        )
        self.color_menu.pack(side="left")

        scroll = ctk.CTkScrollableFrame(self, height=260)
        scroll.pack(fill="both", expand=True, padx=20, pady=10)

        for c in concerts:
            cid = c[0]
            dt = c[1]
            loc = c[2]
            notes = c[3] if len(c) > 3 else ""
            event_id = c[4] if len(c) > 4 else ""
            st = c[6] if len(c) > 6 else ""
            synced_badge = "✓ Synced → " if event_id else ""
            label = f"{synced_badge}{dt}  |  {st + ' | ' if st else ''}{loc[:35]}  |  {notes[:35] if notes else '-'}"
            default_check = True if single else not bool(event_id)
            var = tk.BooleanVar(value=default_check)
            cb = ctk.CTkCheckBox(scroll, text=label, variable=var,
                                 font=ctk.CTkFont(size=12))
            cb.pack(anchor="w", pady=4, padx=10)
            if single:
                cb.configure(state="disabled")
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
        self.selected_color = self.color_map.get(self.color_var.get(), "")
        self.destroy()

    def get_selected(self) -> List[tuple]:
        return [c for c in self._concerts
                if any(c[0] == cid and var.get() for cid, var in self._pairs)]


class EditConcertDialog(ctk.CTkToplevel):
    def __init__(self, parent, cid: int, date: str, loc: str, notes: str,
                 start_time: str, end_time: str, color: str):
        super().__init__(parent)
        self.title("Edit Concert")
        self.geometry("420x420")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.saved = False
        self.cid = cid

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        ctk.CTkLabel(self, text="Edit Concert Details",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 15))

        pad = {"padx": 20, "pady": 8, "fill": "x"}

        # Date
        ctk.CTkLabel(self, text="Date (YYYY-MM-DD):", anchor="w").pack(**pad)
        self.date_var = tk.StringVar(value=date)
        ctk.CTkEntry(self, textvariable=self.date_var).pack(**pad)

        # Start time
        ctk.CTkLabel(self, text="Start time (HH:MM):", anchor="w").pack(**pad)
        self.start_var = tk.StringVar(value=start_time)
        ctk.CTkEntry(self, textvariable=self.start_var).pack(**pad)

        # End time
        ctk.CTkLabel(self, text="End time (HH:MM):", anchor="w").pack(**pad)
        self.end_var = tk.StringVar(value=end_time)
        ctk.CTkEntry(self, textvariable=self.end_var).pack(**pad)

        # Location
        ctk.CTkLabel(self, text="Venue:", anchor="w").pack(**pad)
        self.loc_var = tk.StringVar(value=loc)
        ctk.CTkEntry(self, textvariable=self.loc_var).pack(**pad)

        # Notes
        ctk.CTkLabel(self, text="Notes:", anchor="w").pack(**pad)
        self.notes_var = tk.StringVar(value=notes)
        ctk.CTkEntry(self, textvariable=self.notes_var).pack(**pad)

        # Color
        ctk.CTkLabel(self, text="Calendar color:", anchor="w").pack(**pad)
        self.color_var = tk.StringVar(value=EVENT_COLORS.get(color, "Default"))
        color_options = [f"{v} ({k})" if k else v for k, v in EVENT_COLORS.items()]
        self.color_map = {f"{v} ({k})" if k else v: k for k, v in EVENT_COLORS.items()}
        ctk.CTkOptionMenu(self, values=color_options, variable=self.color_var).pack(**pad)

        btn_f = ctk.CTkFrame(self, fg_color="transparent")
        btn_f.pack(fill="x", padx=20, pady=20)

        ctk.CTkButton(btn_f, text="Cancel", width=100,
                      fg_color="transparent", border_width=1,
                      command=self.destroy).pack(side="right", padx=10)

        ctk.CTkButton(btn_f, text="Save", width=100,
                      command=self._save).pack(side="right", padx=10)

    def _save(self):
        from app.database import update_concert
        date = self.date_var.get().strip()
        start = self.start_var.get().strip()
        end = self.end_var.get().strip()
        loc = self.loc_var.get().strip()
        notes = self.notes_var.get().strip()
        color = self.color_map.get(self.color_var.get(), "")

        if not date or not loc:
            messagebox.showwarning("Missing fields", "Date and Venue are required.")
            return
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("Invalid date", "Date must be YYYY-MM-DD.")
            return
        if start:
            try:
                datetime.strptime(start, "%H:%M")
            except ValueError:
                messagebox.showwarning("Invalid time", "Start time must be HH:MM.")
                return
        if end:
            try:
                datetime.strptime(end, "%H:%M")
            except ValueError:
                messagebox.showwarning("Invalid time", "End time must be HH:MM.")
                return

        update_concert(self.cid, date, loc, notes, start, end, color)
        self.saved = True
        self.destroy()


def main():
    app = ConcertDiaryApp()
    app.mainloop()


if __name__ == "__main__":
    main()
