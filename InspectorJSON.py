import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import tkinter.font as tkFont
import json
import pandas as pd

class JSONCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Inspector JSON")
        # sensible starting size
        self.root.geometry("1000x600")
        self.df = None
        self.orig_format = None   # 'dict' or 'list'
        self.setup_ui()
        self.center_window()

    def setup_ui(self):
        top = ttk.Frame(self.root)
        top.pack(padx=10, pady=5, fill="x")
        ttk.Button(top, text="Load JSON",      command=self.load_json).pack(side="left")
        ttk.Button(top, text="Show All",       command=self.show_all).pack(side="left", padx=5)
        ttk.Button(top, text="Reorder Fields", command=self.reorder_fields).pack(side="left", padx=5)
        ttk.Button(top, text="Save JSON",      command=self.save_json).pack(side="left")
        self.count_var = tk.StringVar(value="Total: 0")
        ttk.Label(top, textvariable=self.count_var).pack(side="left", padx=20)

        self.dynamic_frame = ttk.Frame(self.root)
        self.dynamic_frame.pack(padx=10, pady=5, fill="x")

        tf = ttk.Frame(self.root)
        tf.pack(padx=10, pady=5, fill="both", expand=True)
        self.tree = ttk.Treeview(tf, show="headings")
        vsb = ttk.Scrollbar(tf, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(tf, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tf.grid_rowconfigure(0, weight=1)
        tf.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Control-c>", self.copy_selection)
        self.tree.bind("<Double-1>", self.on_double_click)

    def center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def load_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        self._load_data_from_path(path)

    def load_json_file(self, path):
        """Load JSON directly from a given filepath (for drag-and-drop)."""
        self._load_data_from_path(path)

    def _load_data_from_path(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON: {e}")
            return

        self.orig_format = 'dict' if isinstance(data, dict) else 'list'
        records = []
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, dict):
                    rec = {'ID key': k}
                    rec.update(v)
                    records.append(rec)
        else:
            for item in data:
                if isinstance(item, dict):
                    if 'key' in item and 'ID key' not in item:
                        item['ID key'] = item.pop('key')
                    records.append(item)

        self.df = pd.DataFrame(records)
        self.build_dynamic_buttons()
        self.show_treeview(self.df)
        self.center_window()

    def show_all(self):
        if self.df is None:
            messagebox.showerror("Error", "No data loaded.")
        else:
            self.show_treeview(self.df)
            self.center_window()

    def build_dynamic_buttons(self):
        for w in self.dynamic_frame.winfo_children():
            w.destroy()
        if self.df is None:
            return
        cols = list(self.df.columns)
        for title, func in [('Missing', self.show_missing),
                            ('Unique',  self.show_unique),
                            ('Filter',  self.filter_dialog)]:
            fr = ttk.LabelFrame(self.dynamic_frame, text=title)
            fr.pack(side="left", padx=5, pady=5, fill="y")
            for col in cols:
                ttk.Button(fr, text=col, command=lambda c=col, f=func: f(c))\
                    .pack(fill="x", padx=2, pady=2)

    def show_treeview(self, df):
        self.tree.delete(*self.tree.get_children())
        display = df.fillna("")  # blanks for missing
        cols = list(display.columns)
        self.tree["columns"] = cols

        style = ttk.Style()
        font = tkFont.nametofont(style.lookup("Treeview", "font") or "TkTextFont")

        for col in cols:
            self.tree.heading(col, text=col,
                command=lambda c=col: self.treeview_sort_column(c, False))
            self.tree.column(col, anchor="w", stretch=False, width=0)

        for idx, row in display.iterrows():
            self.tree.insert('', 'end', iid=str(idx),
                             values=[str(v) for v in row])

        self.tree.update_idletasks()

        for col in cols:
            max_w = font.measure(col)
            for val in display[col]:
                w = font.measure(str(val))
                if w > max_w:
                    max_w = w
            self.tree.column(col, width=max_w + 10, stretch=False)

        self.count_var.set(f"Total: {len(display)}")

    def treeview_sort_column(self, col, reverse):
        data = [(self.tree.set(i, col), i) for i in self.tree.get_children('')]
        try:
            data.sort(key=lambda x: float(x[0]) if x[0] else float("-inf"), reverse=reverse)
        except:
            data.sort(key=lambda x: x[0], reverse=reverse)
        for idx, (_, item) in enumerate(data):
            self.tree.move(item, '', idx)
        self.tree.heading(col, command=lambda: self.treeview_sort_column(col, not reverse))

    def copy_selection(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        rows = [self.tree.item(i, 'values') for i in sel]
        text = "\n".join("\t".join(map(str, r)) for r in rows)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def on_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        x, y, width, height = self.tree.bbox(row_id, col_id)
        col_index = int(col_id.replace("#","")) - 1
        col_name = self.tree["columns"][col_index]
        old_val = self.tree.set(row_id, col_name)

        entry = ttk.Entry(self.tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, old_val)
        entry.focus_set()

        def save_edit(e):
            new_val = entry.get()
            self.tree.set(row_id, col_name, new_val)
            try:
                self.df.at[int(row_id), col_name] = new_val
            except:
                pass
            entry.destroy()

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)

    def show_missing(self, field):
        if self.df is not None:
            mask = self.df[field].isna() | (self.df[field] == "")
            self.show_treeview(self.df[mask])
            self.center_window()

    def show_unique(self, field):
        s = self.df[field].dropna()
        items = []
        for v in s:
            if isinstance(v, (list, tuple, set)):
                items.extend(v)
            else:
                items.append(v)
        vals = sorted(set(items), key=lambda x: str(x))
        messagebox.showinfo(f"Unique values for {field}", "\n".join(map(str, vals)))

    def filter_dialog(self, field):
        pop = tk.Toplevel(self.root)
        pop.title(f"Filter {field}")
        ttk.Label(pop, text=f"Filter {field}:").pack(padx=10, pady=5)
        ent = ttk.Entry(pop)
        ent.pack(padx=10, pady=5)
        ent.focus_set()
        ttk.Button(pop, text="OK", command=lambda: go()).pack(pady=5)

        def go():
            val = ent.get().strip()
            pop.destroy()
            if val:
                sub = self.df[self.df[field].astype(str).str.contains(val, case=False, na=False)]
                self.show_treeview(sub)
                self.center_window()

        pop.transient(self.root)
        pop.grab_set()
        pop.wait_window()

    def reorder_fields(self):
        if self.df is None:
            messagebox.showerror("Error", "No data loaded.")
            return

        cols = list(self.df.columns)
        font = tkFont.nametofont("TkTextFont")
        max_char = max(len(str(c)) for c in cols)
        width_chars = max_char + 4
        height_lines = min(len(cols), 20)

        pop = tk.Toplevel(self.root)
        pop.title("Reorder Fields")

        lb = tk.Listbox(pop, width=width_chars, height=height_lines)
        lb.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        for col in cols:
            lb.insert("end", col)

        fr = ttk.Frame(pop)
        fr.pack(side="left", padx=5, pady=5, fill="y")

        def move(dx):
            sel = lb.curselection()
            if not sel:
                return
            i = sel[0]
            j = i + dx
            if j < 0 or j >= lb.size():
                return
            txt = lb.get(i)
            lb.delete(i)
            lb.insert(j, txt)
            lb.selection_set(j)

        ttk.Button(fr, text="Up",   command=lambda: move(-1)).pack(fill="x", pady=2)
        ttk.Button(fr, text="Down", command=lambda: move(1)).pack(fill="x", pady=2)
        ttk.Button(pop, text="Apply", command=lambda: apply_order()).pack(side="bottom", pady=5)

        def apply_order():
            new_cols = [lb.get(i) for i in range(lb.size())]
            self.df = self.df.reindex(columns=new_cols)
            pop.destroy()
            self.build_dynamic_buttons()
            self.show_treeview(self.df)
            self.center_window()

        pop.transient(self.root)
        pop.grab_set()
        pop.wait_window()

    def save_json(self):
        if self.df is None:
            messagebox.showerror("Error", "No data to save.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON","*.json")])
        if not path:
            return

        df_clean = self.df.fillna('')
        recs = df_clean.to_dict(orient='records')

        if self.orig_format == 'dict':
            out = {r['ID key']: {k: v for k, v in r.items() if k != 'ID key'} for r in recs}
        else:
            out = []
            for r in recs:
                entry = r.copy()
                if 'ID key' in entry:
                    entry['key'] = entry.pop('ID key')
                out.append(entry)

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(out, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Saved", f"Saved to {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save JSON: {e}")

def main():
    root = tk.Tk()
    app = JSONCheckerApp(root)
    # support drag-and-drop of a .json onto the exe
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith('.json'):
        app.load_json_file(sys.argv[1])
    root.mainloop()

if __name__ == "__main__":
    main()
