"""Delta Force Cleaner - Tk GUI (Tk 8.6, no third-party deps)."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import engine

APP_TITLE = "三角洲行动 卸载工具"
FONT = ("Microsoft YaHei UI", 10)
MONO = ("Consolas", 9)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1000x720")
        self.minsize(860, 600)

        self.scan_result: engine.ScanResult | None = None
        self.ui_queue: queue.Queue = queue.Queue()

        self._build()

    # ---------------- layout ----------------
    def _build(self):
        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure(".", font=FONT)
        style.configure("Head.TLabel", font=("Microsoft YaHei UI", 15, "bold"))
        style.configure("Sub.TLabel", foreground="#555")
        style.configure("Danger.TButton", font=("Microsoft YaHei UI", 10, "bold"))

        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text=APP_TITLE, style="Head.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="彻底卸载《三角洲行动》本体、腾讯 ACE 反作弊驱动/服务，以及 WeGame 与启动器残留。",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(2, 10))

        # admin banner
        self.admin_var = tk.StringVar()
        self.banner = tk.Label(outer, textvariable=self.admin_var, anchor="w", padx=10, pady=6, justify="left", wraplength=900)
        self.banner.pack(fill="x", pady=(0, 10))
        if engine.is_admin():
            self.banner.configure(bg="#e7f6e7", fg="#1d6b1d")
            self.admin_var.set("✔ 已获得管理员权限：可完整清除 ACE 服务与系统目录。")
        else:
            self.banner.configure(bg="#fff3cd", fg="#8a6d00")
            self.admin_var.set(
                "⚠ 未以管理员身份运行：ACE 服务/驱动可能删不掉。点右侧按钮提权重启。"
            )
            ttk.Button(outer, text="以管理员身份重启", command=self._elevate).pack(anchor="e", pady=(0, 8))

        # options
        opts = ttk.LabelFrame(outer, text="清理范围", padding=10)
        opts.pack(fill="x")
        self.var_game = tk.BooleanVar(value=True)
        self.var_ace = tk.BooleanVar(value=True)
        self.var_wg = tk.BooleanVar(value=True)
        self.var_dry = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="游戏本体与启动器数据", variable=self.var_game).grid(row=0, column=0, sticky="w", padx=(0, 18))
        ttk.Checkbutton(opts, text="ACE 反作弊服务/驱动/卸载项", variable=self.var_ace).grid(row=0, column=1, sticky="w", padx=(0, 18))
        ttk.Checkbutton(opts, text="WeGame 残留", variable=self.var_wg).grid(row=0, column=2, sticky="w", padx=(0, 18))
        ttk.Separator(opts, orient="vertical").grid(row=0, column=3, sticky="ns", padx=10)
        ttk.Checkbutton(opts, text="试运行（只扫描不删除）", variable=self.var_dry).grid(row=0, column=4, sticky="w")

        # actions
        bar = ttk.Frame(outer)
        bar.pack(fill="x", pady=10)
        self.btn_scan = ttk.Button(bar, text="① 扫描", command=self.on_scan)
        self.btn_scan.pack(side="left")
        self.btn_run = ttk.Button(bar, text="② 开始卸载", style="Danger.TButton", command=self.on_run, state="disabled")
        self.btn_run.pack(side="left", padx=8)
        self.btn_save = ttk.Button(bar, text="导出报告", command=self.on_save, state="disabled")
        self.btn_save.pack(side="left")
        self.progress = ttk.Progressbar(bar, mode="determinate", length=220)
        self.progress.pack(side="right")

        # summary
        self.summary_var = tk.StringVar(value="点击「扫描」查看将要从本机清除的内容。")
        ttk.Label(outer, textvariable=self.summary_var, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w", pady=(0, 6), fill="x")

        # table
        table_wrap = ttk.Frame(outer)
        table_wrap.pack(fill="both", expand=True)
        cols = ("sel", "kind", "label", "size")
        self.tree = ttk.Treeview(table_wrap, columns=cols, show="headings", selectmode="none")
        self.tree.heading("sel", text="✓")
        self.tree.heading("kind", text="类型")
        self.tree.heading("label", text="项目")
        self.tree.heading("size", text="大小")
        self.tree.column("sel", width=36, anchor="center", stretch=False)
        self.tree.column("kind", width=90, anchor="center", stretch=False)
        self.tree.column("label", width=640)
        self.tree.column("size", width=110, anchor="e", stretch=False)
        vsb = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.bind("<Button-1>", self._toggle_row)

        # log
        logf = ttk.LabelFrame(outer, text="执行日志", padding=6)
        logf.pack(fill="both", expand=False, pady=(10, 0))
        self.log = tk.Text(logf, height=9, font=MONO, bg="#111", fg="#d8d8d8", insertbackground="#fff", wrap="word")
        lvsb = ttk.Scrollbar(logf, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=lvsb.set, state="disabled")
        self.log.pack(side="left", fill="both", expand=True)
        lvsb.pack(side="right", fill="y")

        self.after(80, self._drain)

    # ---------------- helpers ----------------
    def _toggle_row(self, event):
        if not self.tree.identify_column(event.x) == "#1":
            return
        item = self.tree.identify_row(event.y)
        if not item:
            return
        vals = list(self.tree.item(item, "values"))
        vals[0] = "" if vals[0] else "☑"
        self.tree.item(item, values=vals)
        self._refresh_summary()

    def _checked(self):
        out = []
        for iid in self.tree.get_children():
            if self.tree.item(iid, "values")[0]:
                out.append(self.scan_result.items[self.tree.index(iid)])
        return out

    def _write_log(self, msg: str):
        self.log.configure(state="normal")
        self.log.insert("end", f"[{datetime.now():%H:%M:%S}] {msg}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _drain(self):
        try:
            while True:
                kind, payload = self.ui_queue.get_nowait()
                if kind == "log":
                    self._write_log(payload)
                elif kind == "progress":
                    self.progress["value"] = payload
                elif kind == "scan_done":
                    self._render_scan(payload)
                elif kind == "run_done":
                    self._finish_run(payload)
        except queue.Empty:
            pass
        self.after(80, self._drain)

    # ---------------- scan ----------------
    def _opts(self):
        return {
            "include": {
                "game": self.var_game.get(),
                "ace": self.var_ace.get(),
                "wegame": self.var_wg.get(),
            }
        }

    def on_scan(self):
        self.btn_scan.configure(state="disabled")
        self.btn_run.configure(state="disabled")
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self._write_log("开始扫描…")
        self.progress["value"] = 0
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self):
        try:
            def step(label):
                self.ui_queue.put(("log", "  检查 " + label + " …"))

            res = engine.scan(self._opts(), progress=step)
        except Exception as exc:  # noqa: BLE001
            self.ui_queue.put(("log", f"扫描出错：{exc}"))
            self.ui_queue.put(("scan_done", None))
            return
        self.ui_queue.put(("scan_done", res))

    def _render_scan(self, res):
        self.scan_result = res
        self.btn_scan.configure(state="normal")
        if res is None:
            self.summary_var.set("扫描失败，请查看日志。")
            return
        kind_cn = {"service": "服务/驱动", "dir": "目录", "regkey": "注册表", "file": "文件"}
        for idx, item in enumerate(res.items):
            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=("☑", kind_cn.get(item.kind, item.kind), item.label, engine.human_size(item.size) if item.size else "—"),
            )
        for note in res.notes:
            self._write_log("· " + note)
        if res.items:
            self._write_log(f"扫描完成：共 {len(res.items)} 项，可释放约 {engine.human_size(res.total_bytes)}")
        self.btn_run.configure(state="normal" if res.items else "disabled")
        self.btn_save.configure(state="normal")
        self._refresh_summary()

    def _refresh_summary(self):
        if not self.scan_result:
            return
        checked = self._checked()
        total = sum(i.size for i in checked)
        if not self.scan_result.items:
            self.summary_var.set("未发现残留，系统已是干净状态。")
        else:
            self.summary_var.set(
                f"已勾选 {len(checked)}/{len(self.scan_result.items)} 项，预计释放约 {engine.human_size(total)}"
            )

    # ---------------- run ----------------
    def on_run(self):
        items = self._checked()
        if not items:
            messagebox.showinfo(APP_TITLE, "请至少勾选一项。")
            return

        dry = self.var_dry.get()
        freed = engine.human_size(sum(i.size for i in items))
        if not dry:
            has_service = any(i.kind == "service" for i in items)
            detail = f"将永久删除 {len(items)} 项，预计释放 {freed}。"
            if has_service:
                detail += "\n\n其中包含 ACE 内核服务/驱动，删除后需要重启才能彻底生效。"
            if not engine.is_admin():
                detail += "\n\n你当前没有管理员权限，ACE 相关操作很可能失败。"
            detail += "\n\n此操作不可撤销，确定继续？"
            if not messagebox.askyesno(APP_TITLE + " - 确认卸载", detail, icon="warning"):
                return

        self.btn_run.configure(state="disabled")
        self.btn_scan.configure(state="disabled")
        self.progress["value"] = 0
        threading.Thread(target=self._run_worker, args=(items, dry), daemon=True).start()

    def _run_worker(self, items, dry):
        def log(msg):
            self.ui_queue.put(("log", str(msg)))

        try:
            steps = len(items)
            for n, item in enumerate(items, 1):
                self.ui_queue.put(("progress", (n - 1) / steps * 100))
            result = engine.execute(items, log, dry_run=dry)
        except Exception as exc:  # noqa: BLE001
            log(f"执行出错：{exc}")
            result = {"ok": 0, "failed": len(items), "freed": 0}
        self.ui_queue.put(("progress", 100))
        self.ui_queue.put(("run_done", result))

    def _finish_run(self, result):
        self.btn_scan.configure(state="normal")
        self.btn_run.configure(state="normal")
        if self.var_dry.get():
            messagebox.showinfo(APP_TITLE, "试运行完成，未做任何更改。\n取消勾选「试运行」后再执行即可真正卸载。")
            return
        msg = f"卸载完成。\n\n成功：{result['ok']} 项\n失败：{result['failed']} 项\n释放：{engine.human_size(result['freed'])}"
        if result["ok"]:
            msg += "\n\n建议重启一次，让 ACE 内核驱动彻底退出内存。"
        messagebox.showinfo(APP_TITLE, msg)

    # ---------------- misc ----------------
    def on_save(self):
        if not self.scan_result:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本", "*.txt"), ("所有文件", "*.*")],
            initialfile=f"deltaforce-scan-{datetime.now():%Y%m%d-%H%M%S}.txt",
        )
        if not path:
            return
        lines = [
            f"三角洲行动 卸载工具 - 扫描报告",
            f"时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
            f"管理员：{engine.is_admin()}",
            f"项目数：{len(self.scan_result.items)}  预计释放：{engine.human_size(self.scan_result.total_bytes)}",
            "",
        ]
        for item in self.scan_result.items:
            lines.append(f"[{item.kind}] {item.label}  ({engine.human_size(item.size) if item.size else '-'})")
        lines += ["", "备注："] + ["  " + n for n in self.scan_result.notes]
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        self._write_log(f"报告已保存：{path}")

    def _elevate(self):
        if engine.relaunch_as_admin([]):
            self.destroy()
        else:
            messagebox.showerror(APP_TITLE, "提权被取消或失败。")


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
