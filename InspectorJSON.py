import sys
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import tkinter.font as tkFont

class JSONCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Inspector JSON")
        # sensible default size
        self.root.geometry("1000x600")
        # data
        self.records = []            # full list of record dicts
        self.current_records = []    # filtered/subset for display
        self.record_map = {}         # idx → record
        self.columns = []            # current column order
        self.orig_format = None      # 'dict' or 'list'
        # UI
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
        if path:
            self._load_data_from_path(path)

    def load_json_file(self, path):
        self._load_data_from_path(path)

    def _load_data_from_path(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON: {e}")
            return

        # remember original format
        self.orig_format = 'dict' if isinstance(data, dict) else 'list'

        # flatten into list of dicts
        recs = []
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, dict):
                    r = {'ID key': k}
                    r.update(v)
                    recs.append(r)
        else:
            for item in data:
                if isinstance(item, dict):
                    if 'key' in item and 'ID key' not in item:
                        item['ID key'] = item.pop('key')
                    recs.append(item)

        # assign internal _idx and build record_map
        self.records = []
        self.record_map = {}
        for idx, r in enumerate(recs):
            r['_idx'] = idx
            self.records.append(r)
            self.record_map[idx] = r

        # current_records initially full
        self.current_records = list(self.records)

        # determine columns in first-seen order
        cols = []
        for r in self.records:
            for k in r.keys():
                if k not in cols:
                    cols.append(k)
        # drop internal _idx
        if '_idx' in cols:
            cols.remove('_idx')
        self.columns = cols

        # rebuild buttons & table
        self.build_dynamic_buttons()
        self.show_treeview(self.current_records)
        self.center_window()

    def show_all(self):
        if not self.records:
            messagebox.showerror("Error", "No data loaded.")
        else:
            self.current_records = list(self.records)
            self.show_treeview(self.current_records)
            self.center_window()

    def build_dynamic_buttons(self):
        for w in self.dynamic_frame.winfo_children():
            w.destroy()
        if not self.columns:
            return
        for title, func in [
            ('Missing', self.show_missing),
            ('Unique',  self.show_unique),
            ('Filter',  self.filter_dialog)
        ]:
            fr = ttk.LabelFrame(self.dynamic_frame, text=title)
            fr.pack(side="left", padx=5, pady=5, fill="y")
            for col in self.columns:
                ttk.Button(fr, text=col, command=lambda c=col, f=func: f(c))\
                    .pack(fill="x", padx=2, pady=2)

    def show_treeview(self, records):
        self.tree.delete(*self.tree.get_children())
        # prepare display records (missing → blank)
        style = ttk.Style()
        font = tkFont.nametofont(style.lookup("Treeview", "font") or "TkTextFont")
        # set columns
        self.tree['columns'] = self.columns
        # headings & zero-width
        for col in self.columns:
            self.tree.heading(col, text=col,
                              command=lambda c=col: self.treeview_sort_column(c, False))
            self.tree.column(col, anchor='w', stretch=False, width=0)
        # insert rows
        for r in records:
            iid = str(r['_idx'])
            vals = [str(r.get(col, '') or '') for col in self.columns]
            self.tree.insert('', 'end', iid=iid, values=vals)
        self.tree.update_idletasks()
        # auto-size
        for col in self.columns:
            max_w = font.measure(col)
            for r in records:
                w = font.measure(str(r.get(col, '') or ''))
                if w > max_w:
                    max_w = w
            self.tree.column(col, width=max_w+10, stretch=False)
        # update count
        self.count_var.set(f"Total: {len(records)}")

    def treeview_sort_column(self, col, reverse):
        children = self.tree.get_children('')
        data = [(self.tree.set(i, col), i) for i in children]
        try:
            data.sort(key=lambda x: float(x[0]) if x[0] else float('-inf'), reverse=reverse)
        except:
            data.sort(key=lambda x: x[0], reverse=reverse)
        for idx, (_, iid) in enumerate(data):
            self.tree.move(iid, '', idx)
        self.tree.heading(col, command=lambda: self.treeview_sort_column(col, not reverse))

    def copy_selection(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        rows = [self.tree.item(i, 'values') for i in sel]
        text = "\n".join("\t".join(r) for r in rows)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def on_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        row = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        x,y,wid,ht = self.tree.bbox(row, col)
        ci = int(col.replace('#','')) - 1
        col_name = self.columns[ci]
        old = self.tree.set(row, col_name)
        entry = ttk.Entry(self.tree)
        entry.place(x=x, y=y, width=wid, height=ht)
        entry.insert(0, old)
        entry.focus_set()
        def save(e):
            nv = entry.get()
            self.tree.set(row, col_name, nv)
            idx = int(row)
            rec = self.record_map.get(idx)
            if rec is not None:
                rec[col_name] = nv
            entry.destroy()
        entry.bind("<Return>", save)
        entry.bind("<FocusOut>", save)

    def show_missing(self, field):
        self.current_records = [
            r for r in self.records
            if (r.get(field,'') or '') == ''
        ]
        self.show_treeview(self.current_records)
        self.center_window()

    def show_unique(self, field):
        vals = []
        for r in self.records:
            v = r.get(field)
            if v is None or v == '':
                continue
            if isinstance(v, (list,tuple,set)):
                vals.extend(v)
            else:
                vals.append(v)
        uniques = sorted({str(x) for x in vals})
        messagebox.showinfo(f"Unique values for {field}", "\n".join(uniques))

    def filter_dialog(self, field):
        pop = tk.Toplevel(self.root)
        pop.title(f"Filter {field}")
        ttk.Label(pop, text=f"Filter {field}:").pack(padx=10, pady=5)
        ent = ttk.Entry(pop); ent.pack(padx=10, pady=5); ent.focus_set()
        ttk.Button(pop, text="OK", command=lambda: go()).pack(pady=5)
        def go():
            val = ent.get().strip().lower()
            pop.destroy()
            if val:
                self.current_records = [
                    r for r in self.records
                    if val in str(r.get(field,'')).lower()
                ]
                self.show_treeview(self.current_records)
                self.center_window()
        pop.transient(self.root); pop.grab_set(); pop.wait_window()

    def reorder_fields(self):
        if not self.columns:
            messagebox.showerror("Error", "No data loaded.")
            return
        cols = list(self.columns)
        font = tkFont.nametofont("TkTextFont")
        maxc = max(len(str(c)) for c in cols)
        wchars = maxc + 4
        hlines = min(len(cols),20)
        pop = tk.Toplevel(self.root)
        pop.title("Reorder Fields")
        lb = tk.Listbox(pop, width=wchars, height=hlines)
        lb.pack(side="left", fill="both", expand=True, padx=5,pady=5)
        for c in cols: lb.insert("end", c)
        fr = ttk.Frame(pop); fr.pack(side="left", padx=5,pady=5, fill="y")
        def move(dx):
            sel = lb.curselection()
            if not sel: return
            i = sel[0]; j = i+dx
            if j<0 or j>=lb.size(): return
            txt = lb.get(i)
            lb.delete(i); lb.insert(j, txt); lb.selection_set(j)
        ttk.Button(fr, text="Up",   command=lambda: move(-1)).pack(fill="x", pady=2)
        ttk.Button(fr, text="Down", command=lambda: move(1 )).pack(fill="x", pady=2)
        ttk.Button(pop, text="Apply", command=lambda: apply_order()).pack(side="bottom", pady=5)
        def apply_order():
            self.columns = [lb.get(i) for i in range(lb.size())]
            pop.destroy()
            self.build_dynamic_buttons()
            self.show_treeview(self.current_records)
            self.center_window()
        pop.transient(self.root); pop.grab_set(); pop.wait_window()

    def save_json(self):
        if not self.records:
            messagebox.showerror("Error", "No data to save.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON","*.json")])
        if not path:
            return
        # prepare output
        out = None
        if self.orig_format == 'dict':
            out = {}
            for r in self.records:
                key = r.get('ID key')
                if key is None:
                    continue
                obj = {k:v for k,v in r.items() if k not in ('ID key','_idx')}
                out[key] = obj
        else:
            out = []
            for r in self.records:
                rec = {k:v for k,v in r.items() if k!='_idx'}
                if 'ID key' in rec:
                    rec['key'] = rec.pop('ID key')
                out.append(rec)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(out, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Saved", f"Saved to {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save JSON: {e}")

def main():
    root = tk.Tk()
    app = JSONCheckerApp(root)
    # drag-and-drop support
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith('.json'):
        app.load_json_file(sys.argv[1])
    root.mainloop()

if __name__ == "__main__":
    main()
