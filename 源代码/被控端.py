# 依赖导入检查，提前捕获缺失依赖
try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    import win32gui
    import win32con
    import win32process
    import psutil
    import socket
    import threading
    from PIL import Image, ImageDraw
    import pystray
except ImportError as e:
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "依赖缺失",
        f"缺少依赖库：{e.name}\n请执行：\npip install pywin32 pillow pystray psutil"
    )
    exit()

# ===================== 配置项 =====================
LISTEN_PORT = 9999
BROADCAST_CMD = b"MINIMIZE_SELECTED_APP"
# ==================================================

class ControlledApp:
    def __init__(self, root):
        self.root = root
        self.root.title("被控端")
        self.root.geometry("420x240")
        self.root.resizable(False, False)

        # 核心变量
        self.window_list = []
        self.selected_hwnd = None
        self.selected_title = ""
        self.running = True
        self.udp_socket = None
        self.tray_icon = None
        self.tray_thread = None
        self.operation_mode = tk.StringVar(value="minimize")

        # 初始化ttk样式（解决Radiobutton字体问题）
        self.init_ttk_style()
        self.init_ui()

        # UDP监听
        self.listen_thread = threading.Thread(target=self.udp_listen, daemon=True)
        self.listen_thread.start()

        self.window_check_timer()

        # 关闭按钮 → 最小化到托盘
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

    def init_ttk_style(self):
        """初始化ttk组件样式，统一字体"""
        style = ttk.Style(self.root)
        # 设置全局ttk字体（兼容所有ttk组件）
        style.configure(".", font=("微软雅黑", 9))
        # 单独设置Radiobutton字体（可选，确保生效）
        style.configure("TRadiobutton", font=("微软雅黑", 9))
        # 设置Label字体
        style.configure("TLabel", font=("微软雅黑", 10))
        # 设置Button字体
        style.configure("TButton", font=("微软雅黑", 10))
        # 设置Combobox字体
        style.configure("TCombobox", font=("微软雅黑", 10))

    def init_ui(self):
        # 软件选择标签（改用ttk.Label，统一样式）
        ttk.Label(self.root, text="选择要控制的软件：").place(x=20, y=20)
        self.app_combobox = ttk.Combobox(self.root, state="readonly", width=38)
        self.app_combobox.place(x=20, y=45)

        # 操作模式标签
        ttk.Label(self.root, text="接收到指令时：").place(x=20, y=90)
        # 修复：移除font参数，改用样式控制
        ttk.Radiobutton(
            self.root, text="最小化目标窗口",
            variable=self.operation_mode, value="minimize"
        ).place(x=20, y=115)
        ttk.Radiobutton(
            self.root, text="结束目标窗口进程",
            variable=self.operation_mode, value="close"
        ).place(x=180, y=115)

        self.refresh_btn = ttk.Button(self.root, text="刷新软件列表", command=self.refresh_window_list)
        self.refresh_btn.place(x=20, y=155, width=130)
        self.confirm_btn = ttk.Button(self.root, text="确认选择", command=self.confirm_select)
        self.confirm_btn.place(x=165, y=155, width=130)

        self.status_label = ttk.Label(self.root, text="状态：未选择目标软件", foreground="gray")
        self.status_label.place(x=20, y=200)

        self.refresh_window_list()

    def enum_windows_callback(self, hwnd, extra):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd).strip()
        if not title:
            return True
        blacklist = ["Program Manager", "Windows 输入体验", "Microsoft Text Input Application", "桌面窗口管理器"]
        if title in blacklist:
            return True
        self.window_list.append((title, hwnd))
        return True

    def refresh_window_list(self):
        self.window_list = []
        win32gui.EnumWindows(self.enum_windows_callback, None)
        self.app_combobox['values'] = [t for t, h in self.window_list]
        if not self.window_list:
            self.app_combobox.set("")
            self.selected_hwnd = None
            self.selected_title = ""
            self.status_label.config(text="状态：未找到可用窗口", foreground="red")
            return

        if self.selected_title:
            for idx, (t, h) in enumerate(self.window_list):
                if t == self.selected_title and win32gui.IsWindow(h):
                    self.app_combobox.current(idx)
                    self.status_label.config(text=f"状态：已保留【{self.selected_title}】", foreground="blue")
                    return

        self.app_combobox.current(0)
        self.status_label.config(text="状态：已刷新列表", foreground="blue")

    def confirm_select(self):
        idx = self.app_combobox.current()
        if idx < 0:
            messagebox.showwarning("提示", "请选择软件")
            return
        self.selected_title, self.selected_hwnd = self.window_list[idx]
        self.status_label.config(text=f"状态：已选中【{self.selected_title}】", foreground="green")

    def execute_operation(self):
        if not self.selected_hwnd or not win32gui.IsWindow(self.selected_hwnd):
            self.status_label.config(text="状态：目标窗口无效，请重新选择", foreground="red")
            self.selected_hwnd = None
            self.selected_title = ""
            return

        if self.operation_mode.get() == "minimize":
            win32gui.ShowWindow(self.selected_hwnd, win32con.SW_MINIMIZE)
            self.status_label.config(text=f"状态：已最小化【{self.selected_title}】", foreground="green")
        else:
            try:
                _, pid = win32process.GetWindowThreadProcessId(self.selected_hwnd)
                p = psutil.Process(pid)
                p.terminate()
                self.status_label.config(text=f"状态：已结束【{self.selected_title}】进程", foreground="green")
                self.selected_hwnd = None
                self.selected_title = ""
            except Exception as e:
                self.status_label.config(text=f"状态：结束失败：{str(e)}", foreground="red")

    def udp_listen(self):
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.udp_socket.bind(("0.0.0.0", LISTEN_PORT))
            self.udp_socket.settimeout(1)
            self.root.after(0, lambda: self.status_label.config(
                text=f"状态：已启动监听端口{LISTEN_PORT}", foreground="blue"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("监听失败", f"端口占用：{str(e)}"))
            self.running = False
            return

        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(1024)
                if data == BROADCAST_CMD:
                    self.root.after(0, self.execute_operation)
            except socket.timeout:
                continue
            except Exception:
                break

        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass

    def window_check_timer(self):
        if self.selected_hwnd and not win32gui.IsWindow(self.selected_hwnd):
            self.status_label.config(text="状态：目标窗口已关闭", foreground="red")
            self.selected_hwnd = None
            self.selected_title = ""
        self.root.after(1000, self.window_check_timer)

    # ===================== 托盘功能（已完全修复） =====================
    def create_tray_icon(self):
        """加载自定义图标，失败则用Windows风格默认图标"""
        try:
            # 优先加载自定义ico图标（路径可改）
            image = Image.open("tray_icon.ico")
            return image
        except FileNotFoundError:
            print("未找到自定义图标文件，使用默认图标")
        except Exception as e:
            print(f"图标加载异常：{e}，使用默认图标")

        # 新默认图标：Windows风格蓝色程序图标（32×32高清）
        icon_size = 32
        img = Image.new('RGB', (icon_size, icon_size), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        # 绘制蓝色主方块（带轻微圆角，更贴近Windows风格）
        # 位置：居中，留边距，避免贴边
        padding = 4
        rect_x0 = padding
        rect_y0 = padding
        rect_x1 = icon_size - padding
        rect_y1 = icon_size - padding
        # 圆角矩形（radius=3，轻微圆角更自然）
        draw.rounded_rectangle(
            (rect_x0, rect_y0, rect_x1, rect_y1),
            radius=3,
            fill=(0, 120, 215),  # Windows经典蓝
            outline=(0, 80, 160),  # 深色边框增加层次感
            width=1
        )

        # 绘制白色小窗口标识（内部小矩形）
        inner_padding = 8
        inner_x0 = rect_x0 + inner_padding
        inner_y0 = rect_y0 + inner_padding
        inner_x1 = rect_x1 - inner_padding
        inner_y1 = rect_y1 - inner_padding
        draw.rectangle(
            (inner_x0, inner_y0, inner_x1, inner_y1),
            fill=(255, 255, 255),  # 白色
            width=0
        )

        return img

    def minimize_to_tray(self):
        if self.tray_icon:
            return
        self.root.withdraw()
        menu = pystray.Menu(
            pystray.MenuItem("显示窗口", self.show_window),
            pystray.MenuItem("退出程序", self.exit_app)
        )
        self.tray_icon = pystray.Icon("controlled", self.create_tray_icon(), "被控端", menu)
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

    def show_window(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.root.deiconify()
        self.root.lift()

    def exit_app(self, icon=None, item=None):
        self.running = False
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except:
                pass
            self.tray_icon = None
        try:
            if self.udp_socket:
                self.udp_socket.close()
        except:
            pass
        self.root.after(0, self.root.destroy)
# =================================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = ControlledApp(root)
    root.mainloop()