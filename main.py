# main.py｜良級懸賞 POS 系統 — 開班功能（整數版）
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime

# 如果要顯示 LOGO，請先安裝 Pillow：pip install pillow
try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

# 檔案路徑設定
BASE_DIR    = os.path.dirname(__file__)
SESSION_FILE= os.path.join(BASE_DIR, "session.json")
ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
LOGO_PATH   = os.path.join(ASSETS_DIR, "良級logo_png.png")

class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("良級懸賞 POS 系統 — 開班")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # 載入分店/人員清單及上次選擇
        self.load_session()
        # 建介面
        self.build_ui()
        # 啟動時鐘更新
        self.update_clock()

    def load_session(self):
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}

        self.branch_list     = data.get("branch_list", [])
        self.staff_list      = data.get("staff_list", [])
        self.selected_branch = data.get(
            "selected_branch", self.branch_list[0] if self.branch_list else ""
        )
        self.selected_staff  = data.get(
            "selected_staff",  self.staff_list[0]  if self.staff_list else ""
        )
        self.start_cash      = data.get("start_cash", "")
        self.start_datetime  = data.get("start_datetime", "")

    def save_session(self, branch, staff, cash):
        data = {
            "branch_list":      self.branch_list,
            "staff_list":       self.staff_list,
            "selected_branch":  branch,
            "selected_staff":   staff,
            "start_cash":       cash,
            "start_datetime":   datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save_session_lists(self):
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}

        data["branch_list"]     = self.branch_list
        data["staff_list"]      = self.staff_list
        data["selected_branch"] = self.branch_var.get()
        data["selected_staff"]  = self.staff_var.get()
        if hasattr(self, 'start_cash'):
            data['start_cash'] = self.start_cash
        if hasattr(self, 'start_datetime'):
            data['start_datetime'] = self.start_datetime

        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def build_ui(self):
        top = ttk.Frame(self.root)
        top.pack(pady=10)

        if Image and os.path.exists(LOGO_PATH):
            img = Image.open(LOGO_PATH)
            w, h = img.size
            nw = 300
            nh = int(h * nw / w)
            img = img.resize((nw, nh), Image.ANTIALIAS)
            self.logo_img = ImageTk.PhotoImage(img)
            ttk.Label(top, image=self.logo_img).pack()
        else:
            ttk.Label(top, text="良級懸賞 POS 系統", font=("Arial", 20, "bold")).pack()

        ttk.Label(top, text="開班介面", font=("Arial", 16)).pack(pady=(5,0))

        frm_b = ttk.LabelFrame(self.root, text="分店選擇")
        frm_b.pack(fill="x", padx=20, pady=5)
        self.branch_var = tk.StringVar(value=self.selected_branch)
        self.branch_menu = ttk.OptionMenu(
            frm_b, self.branch_var, self.selected_branch, *self.branch_list
        )
        self.branch_menu.pack(side="left", padx=(10,5))
        ttk.Button(frm_b, text="新增分店", command=self.add_branch).pack(side="left", padx=5)
        ttk.Button(frm_b, text="刪除分店", command=self.delete_branch).pack(side="left", padx=5)

        frm_s = ttk.LabelFrame(self.root, text="開班人員")
        frm_s.pack(fill="x", padx=20, pady=5)
        self.staff_var = tk.StringVar(value=self.selected_staff)
        self.staff_menu = ttk.OptionMenu(
            frm_s, self.staff_var, self.selected_staff, *self.staff_list
        )
        self.staff_menu.pack(side="left", padx=(10,5))
        ttk.Button(frm_s, text="新增人員", command=self.add_staff).pack(side="left", padx=5)
        ttk.Button(frm_s, text="刪除人員", command=self.delete_staff).pack(side="left", padx=5)

        frm_c = ttk.Frame(self.root)
        frm_c.pack(fill="x", padx=20, pady=5)
        ttk.Label(frm_c, text="起始零用金：").pack(side="left", padx=(0,5))
        self.cash_var = tk.StringVar(value=str(self.start_cash))
        ttk.Entry(frm_c, textvariable=self.cash_var, width=15).pack(side="left")

        self.time_label = ttk.Label(self.root, text="", font=("Arial", 12))
        self.time_label.pack(pady=5)

        ttk.Button(self.root, text="開始上班", command=self.start_shift).pack(pady=20)

    def update_clock(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=f"目前時間：{now}")
        self.root.after(1000, self.update_clock)

    def refresh_option(self, widget, choices, var):
        menu = widget["menu"]
        menu.delete(0, "end")
        for c in choices:
            menu.add_command(label=c, command=lambda v=c: var.set(v))

    def add_branch(self):
        name = simpledialog.askstring("新增分店", "請輸入分店名稱：", parent=self.root)
        if name and name not in self.branch_list:
            self.branch_list.append(name)
            self.refresh_option(self.branch_menu, self.branch_list, self.branch_var)
            self.branch_var.set(name)
            self.save_session_lists()

    def delete_branch(self):
        sel = self.branch_var.get()
        if sel and messagebox.askyesno("刪除分店", f"確定刪除「{sel}」？", parent=self.root):
            self.branch_list.remove(sel)
            new = self.branch_list[0] if self.branch_list else ""
            self.branch_var.set(new)
            self.refresh_option(self.branch_menu, self.branch_list, self.branch_var)
            self.save_session_lists()

    def add_staff(self):
        name = simpledialog.askstring("新增人員", "請輸入人員名稱：", parent=self.root)
        if name and name not in self.staff_list:
            self.staff_list.append(name)
            self.refresh_option(self.staff_menu, self.staff_list, self.staff_var)
            self.staff_var.set(name)
            self.save_session_lists()

    def delete_staff(self):
        sel = self.staff_var.get()
        if sel and messagebox.askyesno("刪除人員", f"確定刪除「{sel}」？", parent=self.root):
            self.staff_list.remove(sel)
            new = self.staff_list[0] if self.staff_list else ""
            self.staff_var.set(new)
            self.refresh_option(self.staff_menu, self.staff_list, self.staff_var)
            self.save_session_lists()

    def start_shift(self):
        branch = self.branch_var.get()
        staff  = self.staff_var.get()
        cash   = self.cash_var.get().strip()

        if not branch:
            messagebox.showwarning("未選分店", "請先選擇或新增分店！", parent=self.root)
            return
        if not staff:
            messagebox.showwarning("未選人員", "請先選擇或新增人員！", parent=self.root)
            return
        try:
            cash_val = int(cash)
        except:
            messagebox.showwarning("格式錯誤", "請輸入有效的起始零用金（整數）！", parent=self.root)
            return

        self.save_session(branch, staff, cash_val)
        self.root.destroy()
        import inventory
        inv_root = tk.Tk()
        inventory.InventoryApp(inv_root)
        inv_root.mainloop()

if __name__ == "__main__":
    os.makedirs(ASSETS_DIR, exist_ok=True)
    if not os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump({"branch_list": [], "staff_list": []}, f, ensure_ascii=False, indent=2)

    root = tk.Tk()
    MainApp(root)
    root.mainloop()


# inventory.py｜良級懸賞 POS 系統 — 庫存管理功能（關班保留列表）
import os, sys, subprocess, json, tkinter as tk, csv
from tkinter import ttk, filedialog, messagebox
import webbrowser
from datetime import datetime
import logs
import receive

# 確保 openpyxl 安裝
try:
    from openpyxl import load_workbook
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'openpyxl'])
    from openpyxl import load_workbook

# 資料儲存路徑
DATA_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(DATA_DIR, exist_ok=True)
INVENTORY_FILE = os.path.join(DATA_DIR, 'inventory.json')

class InventoryApp:
    def __init__(self, root):
        # ... 前略，保留原本所有功能 ...
        self.root = root
        self.root.title('良級懸賞 POS 系統')
        # 略...
        # (請參考之前完整版，on_close_shift 已修改以下部分)

    # 關班按鈕回呼
    def on_close_shift(self):
        if not messagebox.askyesno('關班確認', '關班後將匯出今日交易與領取報表並關閉系統，是否繼續？'):
            return
        today = datetime.now().strftime('%Y-%m-%d')
        closing_dir = os.path.join(DATA_DIR, 'closing')
        os.makedirs(closing_dir, exist_ok=True)

        # 匯出交易日誌 & 領取紀錄 (同之前實作)
        # ...

        # **不再刪除 session.json，保留分店/人員列表**

        messagebox.showinfo('完成', f'已匯出今日報表至 {closing_dir}，系統即將關閉。')
        self.root.destroy()

# 其他方法與邏輯未變，請整合進您的完整 inventory.py 檔案中。