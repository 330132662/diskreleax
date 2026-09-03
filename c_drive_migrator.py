# -*- coding: utf-8 -*-
r"""
C 盘目录迁移工具（软链接 / Junction 版）

功能：
  1. 扫描 C:\Users 下每个一级目录的磁盘占用，以列表展示。
  2. 双击任意目录进入下级目录，继续计算并显示子文件夹空间占用。
  3. 右键目录项 -> "一键迁移到 C 盘（软链接）"：将源目录内容移到用户自选的
     目标文件夹，并在原位置建立 junction 软链接，使原路径仍然可用。
  4. 迁移前确认路径，迁移后显示处理结果。

运行：需要带 tkinter 的 Python（如 C:\Python313\python.exe c_drive_migrator.py）
说明：junction（mklink /J）在 Windows 上创建不需要管理员权限；但移动系统正在
      占用的文件夹（如 AppData 部分内容）可能失败，请先关闭相关程序。
"""

import os
import sys
import time
import ctypes
import webbrowser
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

FILE_ATTRIBUTE_REPARSE_POINT = 0x400
ROOT_PATH = r"C:\Users"


# --------------------------------------------------------------------------- #
# 工具函数
# --------------------------------------------------------------------------- #
def human_size(n):
    """字节数转人类可读字符串。"""
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if n < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"


def is_junction(path):
    """判断路径是否为 junction / 目录符号链接。"""
    try:
        st = os.lstat(path)
        return bool(st.st_file_attributes & FILE_ATTRIBUTE_REPARSE_POINT)
    except OSError:
        return False


def read_link_target(path):
    try:
        return os.readlink(path)
    except OSError:
        return ""


def calc_dir_size(path):
    """递归计算目录大小（不跟随软链接/junction，避免重复统计）。"""
    total = 0
    files = 0
    dirs = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
                        files += 1
                    elif entry.is_dir(follow_symlinks=False):
                        s, f, d = calc_dir_size(entry.path)
                        total += s
                        files += f
                        dirs += d + 1
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError):
        pass
    return total, files, dirs


def clear_dir_attrs(path):
    """清除目录的只读/系统/隐藏属性，否则 os.rmdir / mklink 可能失败。"""
    try:
        ctypes.windll.kernel32.SetFileAttributesW(path, 0x80)  # FILE_ATTRIBUTE_NORMAL
    except Exception:
        pass


def create_junction(link, target):
    """在原位置创建指向 target 的软链接（junction 优先，失败回退 os.symlink）。

    返回 (成功布尔值, 失败原因文本)。无论哪种方式都会校验确实创建成功。
    """
    # 优先 mklink /J（Windows 下创建目录 junction 无需管理员权限）
    jp = subprocess.run(
        ["cmd", "/c", "mklink", "/J", link, target],
        capture_output=True, text=True, encoding="gbk", errors="replace",
    )
    if jp.returncode == 0 and is_junction(link):
        return True, ""
    err = (jp.stderr or jp.stdout or f"mklink 返回 {jp.returncode}").strip()

    # 回退：os.symlink 创建目录符号链接（可能需开发者模式 / 管理员）
    try:
        if os.path.exists(link):
            clear_dir_attrs(link)
            os.rmdir(link)
        os.symlink(target, link, target_is_directory=True)
        if is_junction(link):
            return True, ""
        err += "；os.symlink 已创建但校验未通过"
    except OSError as ex:
        err += f"；os.symlink 失败：{ex}"
    return False, err


# --------------------------------------------------------------------------- #
# 主程序
# --------------------------------------------------------------------------- #
class MigratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("C 盘目录迁移工具（软链接 / Junction）")
        self.root.geometry("900x560")
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass

        self.current_path = ROOT_PATH
        self.history = []          # 上级目录栈
        self.scan_thread = None
        self.progress_win = None
        self.scan_gen = 0          # 扫描代次：导航时自增，旧扫描结果作废
        self.sizes = {}            # 路径 -> 字节数，用于按大小排序
        self.cache = {}            # 路径 -> (size, files, dirs)，避免重复扫描

        self._build_ui()
        self.refresh()

    # --------------------------- UI 构建 --------------------------- #
    def _build_ui(self):
        frm_top = ttk.Frame(self.root, padding=(8, 8, 8, 4))
        frm_top.pack(fill="x")

        ttk.Button(frm_top, text="← 上级", command=self.go_up, width=8).pack(side="left")
        ttk.Button(frm_top, text="刷新", command=lambda: self.refresh(force=True), width=8).pack(side="left", padx=(6, 0))
        ttk.Label(frm_top, text="当前位置：").pack(side="left", padx=(10, 2))
        self.path_var = tk.StringVar(value=self.current_path)
        ttk.Entry(frm_top, textvariable=self.path_var, state="readonly").pack(
            side="left", fill="x", expand=True
        )

        # 列表
        cols = ("name", "size", "note")
        self.tree = ttk.Treeview(
            self.root, columns=cols, show="headings", selectmode="browse"
        )
        self.tree.heading("name", text="名称")
        self.tree.heading("size", text="大小")
        self.tree.heading("note", text="备注")
        self.tree.column("name", width=320, anchor="w")
        self.tree.column("size", width=140, anchor="e")
        self.tree.column("note", width=300, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=(4, 4))

        vsb = ttk.Scrollbar(self.root, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.on_right_click)

        # 右键菜单
        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(
            label="一键迁移到 C 盘（软链接）", command=self.migrate_selected
        )
        self.menu.add_separator()
        self.menu.add_command(label="打开所在文件夹", command=self.open_in_explorer)

        # 状态栏（左：状态信息；右：版权标识 + 关于按钮）
        self.status_var = tk.StringVar(value="就绪")
        frm_status = tk.Frame(self.root, relief="sunken", bd=1)
        frm_status.pack(fill="x", side="bottom")

        tk.Label(frm_status, textvariable=self.status_var, anchor="w").pack(
            side="left", fill="x", expand=True, padx=(4, 0)
        )
        tk.Label(frm_status, text="版权所属 @北北物联", fg="#555").pack(
            side="right", padx=(0, 6)
        )
        self.about_btn = ttk.Button(
            frm_status, text="关于", width=6, command=self.show_about_menu
        )
        self.about_btn.pack(side="right", padx=(0, 6))

        # 关于菜单（点击“关于”按钮弹出，上下排列）
        self.about_menu = tk.Menu(self.root, tearoff=0)
        self.about_menu.add_command(
            label="码云本版本库地址  https://gitee.com/jeffcat/diskreleax",
            command=lambda: self.open_url("https://gitee.com/jeffcat/diskreleax"),
        )
        self.about_menu.add_command(
            label="北北物联官网  https://www.appppa.cn/",
            command=lambda: self.open_url("https://www.appppa.cn/"),
        )

        # 提示
        ttk.Label(
            self.root,
            text="提示：双击进入子目录；右键目录项可一键迁移（junction 软链接，原路径继续可用）。",
            foreground="#555",
        ).pack(fill="x", padx=8, pady=(0, 4))

    # --------------------------- 关于 --------------------------- #
    def show_about_menu(self):
        """点击“关于”按钮，在按钮下方弹出上下排列的菜单。"""
        btn = self.about_btn
        x = btn.winfo_rootx()
        y = btn.winfo_rooty() + btn.winfo_height()
        self.about_menu.tk_popup(x, y)
        self.about_menu.grab_release()

    def open_url(self, url):
        """在默认浏览器中打开网址。"""
        webbrowser.open(url)

    # --------------------------- 扫描 / 展示 --------------------------- #
    def refresh(self, force=False):
        # 自增代次：使上一个未完成的扫描失效，导航（含「上级」）不再被扫描阻塞
        self.scan_gen += 1
        gen = self.scan_gen
        self.sizes = {}

        self.path_var.set(self.current_path)
        self.tree.delete(*self.tree.get_children())
        try:
            entries = [
                e for e in os.scandir(self.current_path)
                if e.is_dir() or (is_junction(e.path) and os.path.isdir(e.path))
            ]
        except (PermissionError, FileNotFoundError) as ex:
            messagebox.showerror("无法访问", f"无法读取目录：\n{self.current_path}\n\n{ex}")
            return

        entries.sort(key=lambda e: e.name.lower())
        if not entries:
            self.tree.insert("", "end", values=("(空目录)", "", ""))
            self.status_var.set(f"共 0 个文件夹 · {self.current_path}")
            return

        # 已扫描过的目录直接显示缓存结果（上级/重复进入时立即呈现，不再卡扫描）
        need_scan = force
        for e in entries:
            full = e.path
            if is_junction(full):
                target = read_link_target(full)
                self.sizes[full] = 0
                self.tree.insert(
                    "", "end", iid=full,
                    values=(f"{e.name}  [链接]", "→ " + target, "已迁移（软链接）"),
                )
            elif full in self.cache and not force:
                size, files, dirs = self.cache[full]
                self.sizes[full] = size
                note = f"{dirs} 文件夹 / {files} 文件" if (files or dirs) else ""
                self.tree.insert(
                    "", "end", iid=full, values=(e.name, human_size(size), note)
                )
            else:
                need_scan = True
                self.tree.insert(
                    "", "end", iid=full, values=(e.name, "计算中…", "")
                )

        if need_scan:
            self.status_var.set(f"扫描中… 共 {len(entries)} 个文件夹 · {self.current_path}")
            real_entries = [e for e in entries if not is_junction(e.path)]
            self.scan_thread = threading.Thread(
                target=self._scan_worker, args=(real_entries, gen, force), daemon=True
            )
            self.scan_thread.start()
        else:
            # 全部命中缓存：立即按大小排序呈现，上级按钮可瞬切
            self._reorder_by_size()
            self.status_var.set(f"共 {len(entries)} 个文件夹 · 已缓存 · {self.current_path}")

    def _scan_worker(self, entries, gen, force):
        total_all = 0
        for e in entries:
            if gen != self.scan_gen:          # 已被新导航取代，立即退出
                return
            size, files, dirs = calc_dir_size(e.path)
            if gen != self.scan_gen:
                return
            self.cache[e.path] = (size, files, dirs)
            total_all += size
            self.root.after(0, self._update_row, e.path, size, files, dirs)
        if gen != self.scan_gen:
            return
        self.root.after(0, self._scan_done, gen, total_all, len(entries))

    def _update_row(self, path, size, files, dirs):
        if self.tree.exists(path):
            self.sizes[path] = size
            self.tree.set(path, "size", human_size(size))
            if files or dirs:
                self.tree.set(path, "note", f"{dirs} 文件夹 / {files} 文件")

    def _scan_done(self, gen, total_all, count):
        if gen != self.scan_gen:              # 已是过期扫描，忽略
            return
        self._reorder_by_size()
        self.status_var.set(
            f"共 {count} 个文件夹 · 合计 {human_size(total_all)} · {self.current_path}"
        )

    def _reorder_by_size(self):
        """按大小（字节）降序重新排列列表行。"""
        items = self.tree.get_children()
        items_sorted = sorted(
            items, key=lambda i: self.sizes.get(i, 0), reverse=True
        )
        for i in items_sorted:
            self.tree.move(i, "", "end")

    # --------------------------- 导航 --------------------------- #
    def on_double_click(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        path = sel[0]
        if not os.path.isdir(path):
            return
        self.history.append(self.current_path)
        self.current_path = path
        self.refresh()

    def go_up(self):
        if self.history:
            self.current_path = self.history.pop()
            self.refresh()

    def open_in_explorer(self):
        sel = self.tree.selection()
        if not sel:
            return
        path = sel[0]
        try:
            os.startfile(path)
        except OSError as ex:
            messagebox.showerror("打开失败", str(ex))

    # --------------------------- 右键菜单 --------------------------- #
    def on_right_click(self, event):
        row = self.tree.identify_row(event.y)
        if not row:
            return
        self.tree.selection_set(row)
        self.menu.tk_popup(event.x_root, event.y_root)

    # --------------------------- 迁移 --------------------------- #
    def migrate_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        src = sel[0]
        if is_junction(src):
            messagebox.showinfo(
                "已是软链接",
                f"该目录已经是软链接，目标：\n{read_link_target(src)}\n无需再次迁移。",
            )
            return
        if not os.path.isdir(src):
            return

        # 1) 选择目标（父）文件夹
        parent = filedialog.askdirectory(
            title="选择迁移目标的父文件夹（源内容将放入 目标\\源目录名）",
            initialdir="D:/",
        )
        if not parent:
            return
        # 不允许目标位于源目录内部
        src_abs = os.path.abspath(src)
        parent_abs = os.path.abspath(parent)
        if parent_abs == src_abs or parent_abs.startswith(src_abs + os.sep):
            messagebox.showerror("路径非法", "目标文件夹不能在源目录内部。")
            return

        dst = os.path.join(parent, os.path.basename(src.rstrip(os.sep)))
        if os.path.exists(dst) and os.listdir(dst):
            messagebox.showerror(
                "目标已存在",
                f"目标位置已存在且非空：\n{dst}\n请另选父文件夹，或先清空该目录。",
            )
            return

        # 2) 迁移前确认
        size, files, dirs = calc_dir_size(src)
        msg = (
            f"即将迁移目录（junction 软链接方式）：\n\n"
            f"源：{src}\n"
            f"目标：{dst}\n"
            f"大小：约 {human_size(size)}（{dirs} 文件夹 / {files} 文件）\n\n"
            f"原理：源内容移动到目标，原位置建立软链接指向目标，路径保持不变。\n"
            f"确认继续？"
        )
        if not messagebox.askyesno("确认迁移", msg, icon="warning"):
            return

        # 3) 后台执行迁移
        self._show_progress("迁移处理中…", f"{src}\n→\n{dst}")
        threading.Thread(
            target=self._migrate_worker, args=(src, dst), daemon=True
        ).start()

    def _migrate_worker(self, src, dst):
        try:
            os.makedirs(dst, exist_ok=True)

            # 1) 用 robocopy /MOVE 移动内容（返回码 <8 视为成功）
            proc = subprocess.run(
                ["cmd", "/c", "robocopy", src, dst, "/E", "/MOVE",
                 "/R:1", "/W:1", "/NFL", "/NDL", "/NJH", "/NJS"],
                capture_output=True, text=True, encoding="gbk", errors="replace",
            )
            if proc.returncode >= 8:
                raise RuntimeError(
                    f"robocopy 移动失败（返回码 {proc.returncode}）：\n"
                    f"{proc.stderr or proc.stdout or '未知错误'}"
                )

            # 2) 删除源目录残留的空目录树；用户文件夹常带系统/只读属性且可能有
            #    临时占用文件，这里清除属性并重试几次，确保原位置最终被清空。
            for _ in range(6):
                subprocess.run(
                    ["cmd", "/c", "rd", "/s", "/q", src],
                    capture_output=True, text=True, encoding="gbk", errors="replace",
                )
                if not os.path.exists(src):
                    break
                if os.path.exists(src):
                    clear_dir_attrs(src)
                    try:
                        if not os.listdir(src):
                            os.rmdir(src)
                            break
                    except OSError:
                        pass
                time.sleep(0.5)

            # 3) 若源目录仍残留文件（被程序持续占用），不创建链接以免数据丢失
            if os.path.exists(src) and os.listdir(src):
                remain = len(os.listdir(src))
                raise RuntimeError(
                    f"源目录仍有 {remain} 项文件无法移动（可能正被程序占用）。\n"
                    f"已停止创建软链接以保全数据，请关闭占用程序后重试。\n"
                    f"已移动的内容位于：{dst}"
                )
            # 残留的是空目录也一并清除（带属性时 os.rmdir 会失败，需先清属性）
            if os.path.exists(src):
                clear_dir_attrs(src)
                try:
                    os.rmdir(src)
                except OSError:
                    pass

            # 4) 在原位置创建软链接（junction），并校验确实创建成功
            ok, why = create_junction(src, dst)
            if not ok:
                raise RuntimeError(
                    f"原位置软链接创建失败：\n{why}\n数据已安全位于：{dst}"
                )

            self.root.after(0, self._migrate_done, True, src, dst, "")
        except Exception as ex:
            self.root.after(0, self._migrate_done, False, src, dst, str(ex))

    def _migrate_done(self, ok, src, dst, err):
        self._close_progress()
        if ok:
            messagebox.showinfo(
                "迁移完成",
                f"迁移成功！\n\n源：{src}\n目标：{dst}\n\n"
                f"原位置已建立软链接，程序和路径仍可正常访问。",
            )
        else:
            messagebox.showerror(
                "迁移未完成",
                f"迁移过程中出现问题：\n\n{err}\n\n"
                f"请检查后重试。已移动的内容位于：\n{dst}",
            )
        # 回到源所在目录并刷新，让软链接状态立即可见
        self.current_path = os.path.dirname(src.rstrip(os.sep))
        self.history.clear()
        self.refresh()

    # --------------------------- 进度窗 --------------------------- #
    def _show_progress(self, title, text):
        if self.progress_win:
            self._close_progress()
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("380x140")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        ttk.Label(win, text=text, wraplength=340, justify="left",
                  padding=(14, 14, 14, 6)).pack(fill="both", expand=True)
        ttk.Label(win, text="正在处理，请勿关闭此窗口…",
                  foreground="#777").pack(pady=(0, 10))
        self.progress_win = win

    def _close_progress(self):
        if self.progress_win:
            try:
                self.progress_win.destroy()
            except tk.TclError:
                pass
            self.progress_win = None


# --------------------------------------------------------------------------- #
def main():
    try:
        import tkinter  # noqa
    except ImportError:
        print("错误：当前 Python 未包含 tkinter，请使用带 tkinter 的 Python 运行本程序。")
        sys.exit(1)

    if not os.path.isdir(ROOT_PATH):
        print(f"错误：未找到 {ROOT_PATH}")
        sys.exit(1)

    root = tk.Tk()
    app = MigratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
