import os
import sys
import subprocess
import json
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

# 確保 tkcalendar 安裝
try:
    from tkcalendar import DateEntry
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'tkcalendar'])
    from tkcalendar import DateEntry

# 資料儲存路徑
DATA_DIR = os.path.join(os.path.dirname(__file__), 'logs')
RECEIVE_FILE = os.path.join(DATA_DIR, 'receive.json')
INVENTORY_FILE = os.path.join(DATA_DIR, 'inventory.json')

class ReceiveFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.pack(fill='both', expand=True)
        self.data = []
        self.inventory = []
        # 狀態選項
        self.status_options = [
            "已領取", "需回盒", "已回盒", "需叫貨", "已叫貨",
            "維修中", "店面需寄出", "店面已寄出", "已通知倉庫寄送"
        ]
        # 回盒負責人可編輯清單
        self.return_person_options = []
        # 領取方式選項
        self.receive_method_options = ["自取", "寄送"]
        self.load_data()
        self.load_inventory()
        self.build_ui()
        self.refresh()

    def load_data(self):
        self.data = []
        if not os.path.exists(RECEIVE_FILE):
            return
        text = open(RECEIVE_FILE, 'r', encoding='utf-8').read().strip()
        if not text:
            return
        if text.lstrip().startswith('['):
            try:
                arr = json.loads(text)
                if isinstance(arr, list):
                    self.data = arr
                    return
            except json.JSONDecodeError:
                pass
        for line in text.splitlines():
            try:
                obj = json.loads(line)
                self.data.append(obj)
            except:
                continue
        # 收集現有回盒負責人
        persons = set(item.get('return_person', '') for item in self.data if item.get('return_person'))
        self.return_person_options = list(persons)

    def load_inventory(self):
        if os.path.exists(INVENTORY_FILE):
            with open(INVENTORY_FILE, 'r', encoding='utf-8') as f:
                self.inventory = json.load(f)
        else:
            self.inventory = []

    def save_data(self):
        with open(RECEIVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def save_inventory(self):
        with open(INVENTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.inventory, f, ensure_ascii=False, indent=2)

    def build_ui(self):
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(filter_frame, text='起始:').pack(side='left', padx=5)
        self.start_entry = DateEntry(filter_frame, date_pattern='yyyy-MM-dd')
        self.start_entry.pack(side='left', padx=5)
        ttk.Label(filter_frame, text='結束:').pack(side='left', padx=5)
        self.end_entry = DateEntry(filter_frame, date_pattern='yyyy-MM-dd')
        self.end_entry.pack(side='left', padx=5)

        ttk.Label(filter_frame, text='會員ID:').pack(side='left', padx=5)
        self.member_entry = ttk.Entry(filter_frame)
        self.member_entry.pack(side='left', padx=5)
        ttk.Button(filter_frame, text='查詢', command=self.refresh).pack(side='left', padx=10)

        columns = [
            '日期', '會員ID', '商品名稱', '數量', '到期日', '廠商', '商品狀態',
            '回盒負責人', '回盒日期', '已取/寄日期', '領取方式', '備註'
        ]
        self.tree = ttk.Treeview(
            self,
            columns=columns,
            show='headings',
            selectmode='extended'
        )
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor='center', width=100)
        self.tree.pack(fill='both', expand=True, padx=10, pady=5)

        self.tree.bind('<Delete>', lambda e: self.delete_selected())
        self.tree.bind('<Double-1>', self.on_double_click)

        btns = ttk.Frame(self)
        btns.pack(pady=5)
        ttk.Button(btns, text='刪除紀錄', command=self.delete_selected).pack(side='left', padx=10)

    def refresh(self):
        search_member = self.member_entry.get().strip().lower()
        try:
            start_date = datetime.strptime(self.start_entry.get(), '%Y-%m-%d').date()
        except:
            start_date = None
        try:
            end_date = datetime.strptime(self.end_entry.get(), '%Y-%m-%d').date()
        except:
            end_date = None

        self.tree.delete(*self.tree.get_children())
        for idx, item in enumerate(self.data):
            member = item.get('member', '').lower()
            if search_member and search_member not in member:
                continue

            # 處理日期與到期日
            date_str = item.get('日期', '')
            try:
                item_date = datetime.strptime(date_str.split()[0], '%Y-%m-%d').date()
            except:
                item_date = None
            if start_date and (not item_date or item_date < start_date): continue
            if end_date and (not item_date or item_date > end_date): continue
            expire = ''
            if item_date:
                expire = (item_date + timedelta(days=21)).strftime('%Y-%m-%d')

            values = [
                item.get('日期', ''),
                item.get('member', ''),
                item.get('item', ''),
                str(item.get('inventory_qty', item.get('qty', ''))),
                expire,
                item.get('vendor', ''),
                item.get('status', ''),
                item.get('return_person', ''),
                item.get('return_date', ''),
                item.get('picked_sent_date', ''),
                item.get('receive_method', ''),
                item.get('notes', '')
            ]
            self.tree.insert('', 'end', iid=str(idx), values=values)

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        if not messagebox.askyesno('刪除紀錄', f'確定要刪除選中的 {len(sel)} 筆領取紀錄？'):
            return
        for idx in sorted([int(i) for i in sel], reverse=True):
            self.data.pop(idx)
        self.save_data()
        self.refresh()

    def on_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell": return
        rowid = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        col_idx = int(col.replace('#', '')) - 1
        col_name = self.tree['columns'][col_idx]

        x, y, width, height = self.tree.bbox(rowid, column=col)

        if col_name == '商品狀態':
            widget = ttk.Combobox(self.tree, values=self.status_options, state='readonly')
            current = self.tree.set(rowid, col_name)
            widget.set(current)
            widget.place(x=x, y=y, width=width, height=height)
            widget.bind("<<ComboboxSelected>>", lambda e: self.save_cell(rowid, col_name, widget))
            widget.bind("<FocusOut>", lambda e: widget.destroy())
        elif col_name == '回盒負責人':
            widget = ttk.Combobox(self.tree, values=self.return_person_options, state='normal')
            current = self.tree.set(rowid, col_name)
            widget.set(current)
            widget.place(x=x, y=y, width=width, height=height)
            widget.bind("<<ComboboxSelected>>", lambda e: self.save_cell(rowid, col_name, widget))
            widget.bind("<FocusOut>", lambda e: self.save_cell(rowid, col_name, widget))
        elif col_name in ['回盒日期', '已取/寄日期']:
            widget = DateEntry(self.tree, date_pattern='yyyy-MM-dd')
            current = self.tree.set(rowid, col_name)
            try:
                widget.set_date(datetime.strptime(current, '%Y-%m-%d').date())
            except:
                pass
            widget.place(x=x, y=y, width=width, height=height)
            widget.bind("<<DateEntrySelected>>", lambda e: self.save_cell(rowid, col_name, widget))
            widget.bind("<FocusOut>", lambda e: widget.destroy())
        elif col_name == '領取方式':
            widget = ttk.Combobox(self.tree, values=self.receive_method_options, state='readonly')
            current = self.tree.set(rowid, col_name)
            widget.set(current)
            widget.place(x=x, y=y, width=width, height=height)
            widget.bind("<<ComboboxSelected>>", lambda e: self.save_cell(rowid, col_name, widget))
            widget.bind("<FocusOut>", lambda e: widget.destroy())
        else:
            return

    def save_cell(self, rowid, col_name, widget):
        new_val = widget.get()
        self.tree.set(rowid, col_name, new_val)
        idx = int(rowid)
        key_map = {
            '商品狀態': 'status',
            '回盒負責人': 'return_person',
            '回盒日期': 'return_date',
            '已取/寄日期': 'picked_sent_date',
            '領取方式': 'receive_method',
            '備註': 'notes'
        }
        save_key = key_map.get(col_name)
        if save_key:
            self.data[idx][save_key] = new_val
            # 新回盒負責人加入選項
            if col_name == '回盒負責人' and new_val not in self.return_person_options:
                self.return_person_options.append(new_val)
        self.save_data()
        widget.destroy()

# 主程式示例
if __name__ == '__main__':
    root = tk.Tk()
    root.title('商品領取紀錄')
    ReceiveFrame(root)
    root.mainloop()
