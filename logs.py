# logs.py｜良級懸賞 POS 系統 — 修正版：支援負數計算並鎖定「此單總金額」
import os
import json
import re
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

try:
    from tkcalendar import DateEntry
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'tkcalendar'])
    from tkcalendar import DateEntry

BASE_DIR = os.path.dirname(__file__)
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'receive.json')
INVENTORY_FILE = os.path.join(LOG_DIR, 'inventory.json')

os.makedirs(LOG_DIR, exist_ok=True)

# 查詢最後單價
def get_last_unit_price(idx, hole=None):
    if not os.path.exists(LOG_FILE):
        return None
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for line in reversed(lines):
        try:
            rec = json.loads(line)
        except:
            continue
        if rec.get('idx') != idx:
            continue
        if hole is not None and rec.get('hole') != hole:
            continue
        return rec.get('unit_price')
    return None

class LogsFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.pack(fill='both', expand=True)
        self.all_logs = []
        self.member_var = tk.StringVar()
        self.load_all_logs()

        today = datetime.now().strftime('%Y-%m-%d')
        self.start_var = tk.StringVar(value=today)
        self.end_var = tk.StringVar(value=today)

        self.build_ui()
        self.refresh_logs()

        master.bind('<Return>', lambda e: self.refresh_logs())
        self.tree.bind('<Double-1>', self.open_detail)
        self.tree.bind('<<TreeviewSelect>>', lambda e: self.update_sum())
        self.tree.bind('<ButtonPress-1>', self.on_tree_click)
        self.tree.bind('<B1-Motion>', self.on_tree_drag)
        self.tree.bind('<Delete>', self.delete_selected)

    def load_all_logs(self):
        self.all_logs.clear()
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        self.all_logs.append(json.loads(line))
                    except:
                        continue

    def build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill='x', pady=5)
        ttk.Label(top, text='起始：').pack(side='left')
        self.start_cb = DateEntry(top, textvariable=self.start_var, date_pattern='yyyy-MM-dd', width=12)
        self.start_cb.pack(side='left', padx=5)
        ttk.Label(top, text='結束：').pack(side='left')
        self.end_cb = DateEntry(top, textvariable=self.end_var, date_pattern='yyyy-MM-dd', width=12)
        self.end_cb.pack(side='left', padx=5)
        ttk.Label(top, text='會員ID：').pack(side='left', padx=(10,0))
        ttk.Entry(top, textvariable=self.member_var, width=10).pack(side='left')
        ttk.Button(top, text='查詢', command=self.refresh_logs).pack(side='left', padx=10)

        self.sum_var = tk.StringVar(value='應收加總：0')
        ttk.Label(top, textvariable=self.sum_var, foreground='blue').pack(side='right', padx=10)

        cols = ('time','member','item','mode','due')
        self.tree = ttk.Treeview(self, columns=cols, show='headings', height=15)
        headings = ['日期','會員ID','商品','抽賞方式','此單應收']
        widths = [120,100,200,140,100]
        for c,h,w in zip(cols, headings, widths):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor='center')
        self.tree.pack(fill='both', expand=True, padx=10, pady=5)

    def on_tree_click(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self._drag_sel = {row}
            self.tree.selection_set(self._drag_sel)
        else:
            self._drag_sel = set()
            self.tree.selection_remove(self.tree.selection())
        self.update_sum()

    def on_tree_drag(self, event):
        row = self.tree.identify_row(event.y)
        if row and hasattr(self, '_drag_sel') and row not in self._drag_sel:
            self._drag_sel.add(row)
            self.tree.selection_set(tuple(self._drag_sel))
        self.update_sum()

    def refresh_logs(self):
        start, end = self.start_var.get(), self.end_var.get()
        mem = self.member_var.get().strip()
        self.tree.delete(*self.tree.get_children())
        for idx, rec in enumerate(self.all_logs):
            date = rec.get('time','')[:10]
            if not (start <= date <= end):
                continue
            if mem and rec.get('member','') != mem:
                continue
            hole, draws = rec.get('hole',''), rec.get('抽數','')
            mode_str = f"{hole}洞 x {draws}" if hole and draws else ''
            due_str = rec.get('due','')
            self.tree.insert('', 'end', iid=str(idx), values=(date, rec.get('member',''), rec.get('item',''), mode_str, due_str))
        self.update_sum()

    def update_sum(self):
        total = 0
        for iid in self.tree.selection():
            val = self.tree.set(iid, 'due')
            try:
                total += int(val)
            except:
                continue
        self.sum_var.set(f'應收加總：{total}')

    def delete_selected(self, event=None):
        sel = self.tree.selection()
        if sel and messagebox.askyesno('刪除確認','確定刪除此筆紀錄？'):
            self.all_logs.pop(int(sel[0]))
            self.save_all_logs()
            self.refresh_logs()

    def open_detail(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        rec = self.all_logs[idx]
        detail = tk.Toplevel(self)
        detail.title('交易明細')
        detail.transient(self.master)
        detail.grab_set()
        detail.focus_force()

        free = rec.get('free', False)
        v_digits = (detail.register(lambda P: P=='' or re.fullmatch(r"[0]|[1-9]\d*",P)), '%P')
        v_max1   = (detail.register(lambda P: P=='' or (P.isdigit() and int(P)<=1)), '%P')

        try:
            inv = json.load(open(INVENTORY_FILE, 'r', encoding='utf-8'))
            inv_price = int(inv[rec.get('idx',0)].get('點數價',0))
        except:
            inv_price = 0
        up = rec.get('unit_price', 0)
        big = rec.get('大賞', 0)
        small = rec.get('小賞', 0)

        entries = {}
        snapshot = {}

        def update_discount():
            db = int(entries['大賞折點'].get().split('，')[1].replace('點','')) if '，' in entries['大賞折點'].get() else 0
            ds = int(entries['小賞折點'].get().split('，')[1].replace('點','')) if '，' in entries['小賞折點'].get() else 0
            ed = int(entries['額外折點'].get() or 0)
            tot_amt = int(entries['此單總金額'].get() or 0)
            disc = db + ds + ed
            for k in ['折抵點數','此單應收']:
                entries[k].config(state='normal')
            entries['折抵點數'].delete(0,'end'); entries['折抵點數'].insert(0,str(disc))
            entries['此單應收'].delete(0,'end'); entries['此單應收'].insert(0,str(tot_amt-disc))
            for k in ['折抵點數','此單應收']:
                entries[k].config(state='readonly')

        def recalc_amount(event=None):
            try:
                cnt = int(entries['總抽數'].get() or 0)
            except:
                cnt = 0
            entries['此單總金額'].config(state='normal')
            entries['此單總金額'].delete(0,'end')
            entries['此單總金額'].insert(0,str(cnt * up))
            entries['此單總金額'].config(state='readonly')
            update_discount()

        def restore(field):
            entries[field].delete(0,'end'); entries[field].insert(0,snapshot[field]); update_discount()

        def make_update(field, mul, maxv):
            def fn():
                val = entries[field+'輸入'].get()
                if not val.isdigit():
                    messagebox.showwarning('錯誤',f'請輸入{field}數量',parent=detail); return
                cnt = int(val)
                if cnt > maxv:
                    messagebox.showwarning('錯誤',f'{field}不可超過{maxv}',parent=detail); return
                entries[field].delete(0,'end'); entries[field].insert(0,f'{field}{cnt}，{cnt*mul}點'); update_discount()
            return fn

        fields = [
            ('日期', rec.get('time','')[:10], False),
            ('分店', rec.get('branch',''), False),
            ('人員', rec.get('staff',''), False),
            ('會員ID', rec.get('member',''), True),
            ('商品', rec.get('item',''), False),
            ('商品點數價', inv_price, False),
            ('抽賞選擇洞數', rec.get('hole',''), False),
            ('單抽價格', up, False),
            ('總抽數', rec.get('抽數',0), True),
            ('大賞', big, True),
            ('小賞', small, True),
            ('非洲人','免單' if free else '否', False),
            ('大賞折點', f"大賞折點{rec.get('dis_big_cnt',0)}，{rec.get('dis_big_cnt',0)*inv_price}點", True),
            ('小賞折點', f"小賞折點{rec.get('dis_small_cnt',0)}，{rec.get('dis_small_cnt',0)*20}點", True),
            ('額外折點', rec.get('extra_dis',0), True),
            ('折抵原因', rec.get('reason',''), True),
            ('此單總金額', rec.get('total',0), False),  # 鎖定此欄位
            ('折抵點數', rec.get('discount',0), False),
            ('此單應收', rec.get('due',0), False),
            ('現金支付', rec.get('cash',0), True),
            ('匯款支付', rec.get('transfer',0), True),
            ('點數支付', rec.get('points',0), True)
        ]

        for i,(lbl,val,editable) in enumerate(fields):
            ttk.Label(detail,text=lbl).grid(row=i,column=0,sticky='e',padx=5,pady=2)
            ent = ttk.Entry(detail,width=30)
            ent.grid(row=i,column=1,padx=5,pady=2)
            ent.insert(0,str(val))
            if not editable:
                ent.config(state='readonly')
            # 綁定自動計算與驗證
            if lbl == '總抽數':
                ent.bind('<KeyRelease>', recalc_amount)
            if lbl == '大賞':
                ent.config(validate='key', validatecommand=v_max1)
            entries[lbl] = ent
            if lbl in ('大賞折點','小賞折點'):
                ie = ttk.Entry(detail,width=5)
                ie.grid(row=i,column=2)
                ie.bind('<Button-1>', lambda e: e.widget.focus_set())
                entries[lbl+'輸入'] = ie
                if lbl=='小賞折點' and free:
                    ie.config(state='disabled'); ent.config(state='readonly')
                else:
                    maxv = int(entries['大賞'].get()) if lbl=='大賞折點' else int(entries['小賞'].get())
                    mul = inv_price if lbl=='大賞折點' else 20
                    ttk.Button(detail,text='更新',command=make_update(lbl,mul,maxv)).grid(row=i,column=3)
                    ttk.Button(detail,text='復原',command=lambda f=lbl:restore(f)).grid(row=i,column=4)

        # 快照
        for k,v in entries.items(): snapshot[k] = v.get()
        def on_close():
            modified = any(entries[k].get()!=snapshot[k] for k in snapshot)
            if modified and not messagebox.askyesno('尚未儲存','尚未儲存，確定要離開?',parent=detail):
                return
            detail.destroy()
        detail.protocol('WM_DELETE_WINDOW',on_close)
        # 綁定折抵更新
        for fld in ('額外折點', '此單總金額'):
            entries[fld].bind('<KeyRelease>', lambda e: update_discount())

        # 儲存按鈕
        def save():
            try: tot=int(entries['總抽數'].get()); a_big=int(entries['大賞'].get()); a_small=int(entries['小賞'].get())
            except: messagebox.showwarning('錯誤','請輸入有效數字',parent=detail); return
            if a_big+a_small!=tot: messagebox.showwarning('錯誤','大賞+小賞須等於總抽數',parent=detail); return
            update_discount()
            due_val=int(entries['此單應收'].get()); paid=0
            for fld in ('現金支付','匯款支付','點數支付'):
                try: paid+=int(entries[fld].get())
                except: messagebox.showwarning('錯誤',f'請輸入有效數字在{fld}',parent=detail); return
            if paid!=due_val: messagebox.showwarning('錯誤',f'支付總和須等於應收{due_val}',parent=detail); return
            extra=int(entries['額外折點'].get() or 0)
            if extra>0 and not entries['折抵原因'].get().strip(): messagebox.showwarning('錯誤','額外折點大於0時須填寫折抵原因',parent=detail); return
            rec.update({
                'member':entries['會員ID'].get(),'抽數':tot,'大賞':a_big,'小賞':a_small,
                'dis_big_cnt':int(entries['大賞折點'].get().split('，')[0].replace('大賞折點','')),
                'dis_small_cnt':int(entries['小賞折點'].get().split('，')[0].replace('小賞折點','')),
                'extra_dis':extra,'reason':entries['折抵原因'].get(),
                'discount':int(entries['折抵點數'].get()),
                'total':int(entries['此單總金額'].get()),'due':due_val,
                'cash':int(entries['現金支付'].get()),'transfer':int(entries['匯款支付'].get()),'points':int(entries['點數支付'].get())
            })
            self.save_all_logs(); self.refresh_logs(); messagebox.showinfo('成功','已儲存修改',parent=detail); detail.destroy()
        ttk.Button(detail,text='儲存',command=save).grid(row=len(fields),column=0,columnspan=5,pady=10)

    def save_all_logs(self):
        with open(LOG_FILE,'w',encoding='utf-8') as f:
            for rec in self.all_logs:
                f.write(json.dumps(rec, ensure_ascii=False)+'\n')

if __name__=='__main__':
    root = tk.Tk()
    root.title('交易紀錄測試')
    LogsFrame(root)
    root.mainloop()
