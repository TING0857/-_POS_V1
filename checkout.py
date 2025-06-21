# checkout.py｜良級懸賞 POS 系統 — 抽賞結帳（三步驟折點流程）
import os
import json
import re
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime

# 新增：從 logs.py 取得最近一次單抽價
from logs import get_last_unit_price

BASE_DIR       = os.path.dirname(__file__)
SESSION_FILE   = os.path.join(BASE_DIR, "session.json")
INVENTORY_FILE = os.path.join(BASE_DIR, "logs", "inventory.json")
LOG_FILE       = os.path.join(BASE_DIR, "logs", "logs.json")
RECEIVE_FILE   = os.path.join(BASE_DIR, "logs", "receive.json")
REASON_FILE    = os.path.join(BASE_DIR, "logs", "reasons.json")

class CheckoutApp:
    def __init__(self, master, idx):
        self.master = master
        self.idx    = idx
        master.title("良級懸賞 POS 系統 — 抽賞結帳")
        master.geometry("400x580")
        master.attributes('-topmost', True)

        # 共用變數
        self.branch         = tk.StringVar()
        self.staff          = tk.StringVar()
        self.hole_var       = tk.IntVar(value=20)
        self.num_big        = tk.IntVar(value=0)
        self.num_small      = tk.IntVar(value=0)
        self.free_var       = tk.BooleanVar(value=False)
        self.unit_price_var = tk.IntVar()
        self.total_amt      = tk.IntVar(value=0)
        self.dis_big_cnt    = tk.IntVar(value=0)
        self.dis_small_cnt  = tk.IntVar(value=0)
        self.extra_dis      = tk.IntVar(value=0)    # Step2「額外折點」
        self.discount       = tk.IntVar(value=0)
        self.due_amt        = tk.IntVar(value=0)
        self.reason_var     = tk.StringVar()
        self.pay_cash       = tk.IntVar(value=0)
        self.pay_transfer   = tk.IntVar(value=0)
        self.pay_points     = tk.IntVar(value=0)

        self.load_session()
        self.load_inventory()
        self.load_reasons()

        self.clear()
        self.step1_ui()

    def load_session(self):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                sess = json.load(f)
            self.branch.set(sess.get("selected_branch", ""))
            self.staff.set(sess.get("selected_staff", ""))
        except:
            pass

    def load_inventory(self):
        with open(INVENTORY_FILE, "r", encoding="utf-8") as f:
            inv = json.load(f)
        self.item       = inv[self.idx]
        self.base_price = int(self.item.get("點數價", 0))

    def load_reasons(self):
        if os.path.exists(REASON_FILE):
            with open(REASON_FILE, "r", encoding="utf-8") as f:
                self.reasons = json.load(f)
        else:
            self.reasons = []

    def save_reasons(self):
        with open(REASON_FILE, "w", encoding="utf-8") as f:
            json.dump(self.reasons, f, ensure_ascii=False, indent=2)

    def clear(self):
        for w in self.master.winfo_children():
            w.destroy()

    # 驗證：允許輸入 0 或 非零開頭數字，禁止 0 開頭多位數（Step1/Step2 專用）
    def validate_nonneg(self, P):
        return P == "" or P == "0" or (P.isdigit() and not P.startswith("0"))

    # 驗證：允許 0 或 正整數，不會因 '0' 被視為前導零拒絕 （Step3 現金/匯款 專用）
    def validate_nonneg_allow_zero(self, P):
        return P == "" or re.fullmatch(r"[0]|[1-9]\d*", P) is not None

    # 驗證付款欄位可輸入負數 （Step3 點數 專用）
    def validate_pay(self, P):
        if P == "" or P == "-":
            return True
        return re.fullmatch(r"-?[1-9]\d*|0", P) is not None

    # --- Step 1 ---
    def step1_ui(self):
        frm = ttk.Frame(self.master, padding=10)
        frm.pack(fill="both", expand=True)

        vcmd_nlz = (self.master.register(self.validate_nonneg), '%P')

        # 分店 / 人員
        ttk.Label(frm, text="分店：").grid(row=0, column=0, sticky="e")
        ttk.Combobox(frm, textvariable=self.branch,
                     values=self.get_list("branch_list"),
                     state="readonly", width=15).grid(row=0, column=1, pady=5)
        ttk.Label(frm, text="人員：").grid(row=1, column=0, sticky="e")
        ttk.Combobox(frm, textvariable=self.staff,
                     values=self.get_list("staff_list"),
                     state="readonly", width=15).grid(row=1, column=1, pady=5)

        # 商品資訊
        ttk.Label(frm, text="商品：").grid(row=2, column=0, sticky="e")
        ttk.Label(frm, text=self.item.get("商品名稱","")).grid(row=2, column=1, sticky="w")
        ttk.Label(frm, text="商品點數價：").grid(row=3, column=0, sticky="e")
        ttk.Label(frm, text=str(self.base_price)).grid(row=3, column=1, sticky="w")

        # 洞數
        ttk.Label(frm, text="洞數：").grid(row=4, column=0, sticky="e")
        cb_hole = ttk.Combobox(frm, textvariable=self.hole_var,
                               values=[20,40,60,80],
                               state="readonly", width=5)
        cb_hole.grid(row=4, column=1, sticky="w", pady=5)
        cb_hole.bind("<<ComboboxSelected>>", lambda e: self.on_count_change())

        # 單抽價（優先從 logs 取最後一次價格，無則回預設）
        ttk.Label(frm, text="單抽價：").grid(row=5, column=0, sticky="e")
        try:
            last_price = get_last_unit_price(self.idx, self.hole_var.get())
            if last_price is not None:
                self.unit_price_var.set(int(last_price))
            else:
                self.unit_price_var.set(int(self.item.get("20洞價格", self.base_price)))
        except:
            self.unit_price_var.set(int(self.item.get("20洞價格", self.base_price)))
        ttk.Label(frm, textvariable=self.unit_price_var).grid(row=5, column=1, sticky="w")

        # 大賞 / 小賞
        ttk.Label(frm, text="大賞：").grid(row=6, column=0, sticky="e")
        e_big = ttk.Entry(frm, textvariable=self.num_big,
                          validate="key", validatecommand=vcmd_nlz, width=5)
        e_big.grid(row=6, column=1, sticky="w", pady=5)
        e_big.bind("<KeyRelease>", lambda e: self.on_count_change())

        ttk.Label(frm, text="小賞：").grid(row=7, column=0, sticky="e")
        e_small = ttk.Entry(frm, textvariable=self.num_small,
                            validate="key", validatecommand=vcmd_nlz, width=5)
        e_small.grid(row=7, column=1, sticky="w", pady=5)
        e_small.bind("<KeyRelease>", lambda e: self.on_count_change())

        # 免單（狀態由 on_count_change 控制）
        self.chk_free = ttk.Checkbutton(frm, text="非洲人免單",
                                        variable=self.free_var,
                                        command=self.on_count_change)
        self.chk_free.grid(row=8, column=0, columnspan=2, pady=5)

        # 總金額
        ttk.Label(frm, text="此單總金額：").grid(row=9, column=0, sticky="e")
        ttk.Label(frm, textvariable=self.total_amt).grid(row=9, column=1, sticky="w")

        # 下一步
        ttk.Button(frm, text="折點結帳", command=self.goto_step2)\
            .grid(row=10, column=0, columnspan=2, pady=15)

        # 初次計算
        self.on_count_change()

    def on_count_change(self):
        big   = max(0, min(self.num_big.get(), 1))
        hole  = self.hole_var.get()
        small = max(0, min(self.num_small.get(), hole - big))
        self.num_big.set(big)
        self.num_small.set(small)

        # 嘗試從 logs 取最後一次單抽價
        price = None
        try:
            last = get_last_unit_price(self.idx, hole)
            if last is not None:
                price = int(last)
        except:
            price = None

        if price is None:
            price = int(self.item.get(f"{hole}洞價格", self.base_price))

        self.unit_price_var.set(price)
        self.total_amt.set(0 if self.free_var.get() else (big + small) * price)

        if big == 1 and small == hole - 1:
            self.chk_free.state(["!disabled"])
        else:
            self.free_var.set(False)
            self.chk_free.state(["disabled"])

    def get_list(self, key):
        try:
            with open(SESSION_FILE, 'r', encoding="utf-8") as f:
                return json.load(f).get(key, [])
        except:
            return []

    def goto_step1(self):
        self.clear(); self.step1_ui()
    def goto_step2(self):
        self.clear(); self.step2_ui()
    def goto_step3(self):
        self.clear(); self.step3_ui()

    # --- Step 2 ---
    def step2_ui(self):
        self.dis_big_cnt.set(0)
        if self.free_var.get():
            self.dis_small_cnt.set(0)
        self.extra_dis.set(0)    # 重置「額外折點」
        self.discount.set(0)
        self.due_amt.set(self.total_amt.get())

        frm = ttk.Frame(self.master, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text=f"此單總金額：{self.total_amt.get()}")\
            .grid(row=0, column=0, columnspan=2, pady=5)

        self.max_big   = self.num_big.get()
        self.max_small = 0 if self.free_var.get() else self.num_small.get()

        # 大賞折點
        ttk.Label(frm, text="大賞折點數量：").grid(row=1, column=0, sticky="e")
        e1 = ttk.Entry(frm, textvariable=self.dis_big_cnt,
                       validate="key",
                       validatecommand=(self.master.register(self.validate_nonneg), '%P'),
                       width=5)
        e1.grid(row=1, column=1, sticky="w", pady=5)
        e1.bind('<FocusOut>', lambda e: self._clamp(self.dis_big_cnt, self.max_big, "大賞折點數量"))

        # 小賞折點
        ttk.Label(frm, text="小賞折點數量：").grid(row=2, column=0, sticky="e")
        e2 = ttk.Entry(frm, textvariable=self.dis_small_cnt,
                       validate="key",
                       validatecommand=(self.master.register(self.validate_nonneg), '%P'),
                       width=5)
        e2.grid(row=2, column=1, sticky="w", pady=5)
        if self.free_var.get():
            e2.config(state="disabled")
        else:
            e2.config(state="normal")
            e2.bind('<FocusOut>', lambda e: self._clamp(self.dis_small_cnt, self.max_small, "小賞折點數量"))

        # 額外折點
        ttk.Label(frm, text="額外折點：").grid(row=3, column=0, sticky="e")
        e3 = ttk.Entry(frm, textvariable=self.extra_dis,
                       validate="key",
                       validatecommand=(self.master.register(self.validate_nonneg), '%P'),
                       width=7)
        e3.grid(row=3, column=1, sticky="w", pady=5)

        # 折扣原因
        ttk.Label(frm, text="折扣原因：").grid(row=4, column=0, sticky="e")
        ttk.Entry(frm, textvariable=self.reason_var, width=20).grid(row=4, column=1, pady=5)
        ttk.Button(frm, text="新增原因", command=self.add_reason).grid(row=4, column=2, padx=5)
        ttk.Button(frm, text="刪除原因", command=self.delete_reason).grid(row=4, column=3)

        self.reasons_frame = ttk.Frame(frm)
        self.reasons_frame.grid(row=5, column=0, columnspan=4, pady=5)
        self.refresh_reasons()

        ttk.Label(frm, text="折扣點數：").grid(row=6, column=0, sticky="e")
        ttk.Label(frm, textvariable=self.discount).grid(row=6, column=1, sticky="w")
        ttk.Label(frm, text="此單應收：").grid(row=7, column=0, sticky="e")
        ttk.Label(frm, textvariable=self.due_amt).grid(row=7, column=1, sticky="w")

        ttk.Button(frm, text="上一步", command=self.goto_step1).grid(row=8, column=0, pady=15)
        ttk.Button(frm, text="下一步 確認結帳", command=self.goto_step3).grid(row=8, column=1, pady=15)

        self.dis_big_cnt.trace_add('write', lambda *_: self.update_due())
        self.dis_small_cnt.trace_add('write', lambda *_: self.update_due())
        self.extra_dis.trace_add('write', lambda *_: self.update_due())

    def _clamp(self, var, mx, name):
        try:
            v = int(var.get())
        except:
            v = 0
        if v < 0 or v > mx:
            messagebox.showwarning("防呆", f"{name} 不可超過 {mx}", parent=self.master)
            var.set(mx)
        self.update_due()

    def add_reason(self):
        r = simpledialog.askstring("新增原因", "請輸入折扣原因：", parent=self.master)
        if r and r not in self.reasons:
            self.reasons.append(r)
            self.save_reasons()
            self.refresh_reasons()

    def delete_reason(self):
        r = simpledialog.askstring("刪除原因", "請輸入要刪除的原因：", parent=self.master)
        if r in self.reasons:
            self.reasons.remove(r)
            self.save_reasons()
            self.refresh_reasons()

    def refresh_reasons(self):
        for w in self.reasons_frame.winfo_children():
            w.destroy()
        for r in self.reasons:
            btn = ttk.Button(self.reasons_frame, text=r,
                             command=lambda x=r: self.reason_var.set(x))
            btn.pack(side='left', padx=2)

    def update_due(self):
        db = self.dis_big_cnt.get()
        ds = self.dis_small_cnt.get()
        ed = self.extra_dis.get()
        self.discount.set(db*self.base_price + ds*20 + ed)
        self.due_amt.set(self.total_amt.get() - self.discount.get())

    # --- Step 3 ---
    def step3_ui(self):
        frm = ttk.Frame(self.master, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text=f"應收：{self.due_amt.get()}").grid(row=0, column=0, columnspan=2, pady=5)

        # 現金（允許 0）
        ttk.Label(frm, text="現金：").grid(row=1, column=0, sticky="e")
        ttk.Entry(frm, textvariable=self.pay_cash,
                  validate="key", validatecommand=(self.master.register(self.validate_nonneg_allow_zero), '%P'),
                  width=10).grid(row=1, column=1, pady=5)

        # 匯款（允許 0）
        ttk.Label(frm, text="匯款：").grid(row=2, column=0, sticky="e")
        ttk.Entry(frm, textvariable=self.pay_transfer,
                  validate="key", validatecommand=(self.master.register(self.validate_nonneg_allow_zero), '%P'),
                  width=10).grid(row=2, column=1, pady=5)

        # 點數（允許負數）
        ttk.Label(frm, text="點數：").grid(row=3, column=0, sticky="e")
        ttk.Entry(frm, textvariable=self.pay_points,
                  validate="key", validatecommand=(self.master.register(self.validate_pay), '%P'),
                  width=10).grid(row=3, column=1, pady=5)

        ttk.Button(frm, text="上一步", command=self.goto_step2).grid(row=4, column=0, pady=15)
        ttk.Button(frm, text="確認結帳", command=self.do_confirm).grid(row=4, column=1, pady=15)

    def do_confirm(self):
        paid = self.pay_cash.get() + self.pay_transfer.get() + self.pay_points.get()
        if paid != self.due_amt.get():
            messagebox.showwarning("支付錯誤",
                f"支付總和需等於應收 {self.due_amt.get()}！", parent=self.master)
            return
        self.post_confirm()

    def post_confirm(self):
        while True:
            member = simpledialog.askstring("會員ID", "請輸入會員ID (4~5位 或 10位)：", parent=self.master)
            if member is None:
                return
            if re.fullmatch(r"\d{4,5}|\d{10}", member):
                break
            messagebox.showwarning("格式錯誤", "必須輸入4~5位數ID或10位手機號碼", parent=self.master)

        big   = self.num_big.get()
        small = self.num_small.get()
        draws = big + small

        rec = {
            "idx":            self.idx,
            "time":           datetime.now().isoformat(),
            "branch":         self.branch.get(),
            "staff":          self.staff.get(),
            "member":         member,
            "item":           self.item.get("商品名稱",""),
            "hole":           self.hole_var.get(),
            "抽數":           draws,
            "大賞":           big,
            "小賞":           small,
            "free":           self.free_var.get(),
            "inventory_qty":  big if self.free_var.get() else draws,
            "total":          self.total_amt.get(),
            "dis_big_cnt":    self.dis_big_cnt.get(),   # 新增：大賞折點
            "dis_small_cnt":  self.dis_small_cnt.get(), # 新增：小賞折點
            "extra_dis":      self.extra_dis.get(),     # 新增：額外折點
            "discount":       self.discount.get(),
            "reason":         self.reason_var.get(),
            "due":            self.due_amt.get(),
            "cash":           self.pay_cash.get(),
            "transfer":       self.pay_transfer.get(),
            "points":         self.pay_points.get(),
            "unit_price":     self.unit_price_var.get() # 新增：單抽價
        }

        try:
            from logs import add_transaction
            add_transaction(rec)
        except ImportError:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        rec2 = {
            **rec,
            "日期":  datetime.now().strftime('%Y-%m-%d'),
            "qty":   rec["inventory_qty"],
            "expire":datetime.now().date().isoformat()
        }
        with open(RECEIVE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec2, ensure_ascii=False) + "\n")

        try:
            self.master.master.event_generate('<<TransactionDone>>')
        except:
            pass

        messagebox.showinfo("完成", "已完成結帳並儲存紀錄")
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    CheckoutApp(root, idx=0)
    root.mainloop()
