import tkinter as tk
from tkinter import ttk, messagebox
import socket

# ===================== 配置项（必须和被控端完全一致） =====================
TARGET_PORT = 9999  # 目标端口
BROADCAST_CMD = b"MINIMIZE_SELECTED_APP"  # 控制指令
BROADCAST_ADDR = "255.255.255.255"  # 局域网广播地址，无需修改


# ========================================================================

class ControllerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("控制端")
        self.root.geometry("420x220")
        self.root.resizable(False, False)

        # 初始化置顶状态
        self.always_on_top = False
        # 设置循环置顶检测（每100ms检测一次，确保置顶不失效）
        self.check_always_on_top()

        # 初始化UI
        self.init_ui()

    def init_ui(self):
        # 新增置顶切换按钮
        self.top_btn = ttk.Button(
            self.root,
            text="🔼 点击置顶窗口",
            command=self.toggle_always_on_top,
            style="Small.TButton"
        )
        self.top_btn.place(relx=0.5, rely=0.15, anchor="center", width=180, height=30)

        # 核心控制按钮
        self.send_btn = ttk.Button(
            self.root,
            text="一键最小化所有被控端选中的软件",
            command=self.send_broadcast_cmd,
            style="Big.TButton"
        )
        self.send_btn.place(relx=0.5, rely=0.4, anchor="center", width=380, height=70)

        # 状态提示
        self.status_label = ttk.Label(
            self.root,
            text="状态：就绪，确保和被控端在同一局域网、端口一致",
            font=("微软雅黑", 10),
            foreground="gray",
            wraplength=380
        )
        self.status_label.place(relx=0.5, rely=0.75, anchor="center")

        # 按钮样式优化
        style = ttk.Style()
        style.configure("Big.TButton", font=("微软雅黑", 13, "bold"))
        style.configure("Small.TButton", font=("微软雅黑", 9))

    # 切换置顶状态
    def toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        if self.always_on_top:
            self.root.attributes("-topmost", True)
            self.top_btn.config(text="🔽 取消窗口置顶")
            self.status_label.config(text="状态：窗口已置顶，确保和被控端在同一局域网、端口一致", foreground="blue")
        else:
            self.root.attributes("-topmost", False)
            self.top_btn.config(text="🔼 点击置顶窗口")
            self.status_label.config(text="状态：就绪，确保和被控端在同一局域网、端口一致", foreground="gray")

    # 循环检测置顶状态（防止置顶失效）
    def check_always_on_top(self):
        if self.always_on_top:
            # 重新设置置顶，确保不会被其他窗口覆盖
            self.root.attributes("-topmost", True)
        # 每100ms检测一次，实现循环置顶
        self.root.after(100, self.check_always_on_top)

    # 发送广播指令，新增防重复点击、异常全捕获
    def send_broadcast_cmd(self):
        # 点击后立即禁用按钮，防止重复点击
        self.send_btn.config(state="disabled")
        try:
            # 创建UDP socket，开启广播权限
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            # 设置发送超时，避免卡死
            udp_socket.settimeout(2)
            # 发送广播指令
            udp_socket.sendto(BROADCAST_CMD, (BROADCAST_ADDR, TARGET_PORT))
            udp_socket.close()
            # 更新成功状态
            self.status_label.config(text="状态：指令已成功广播，所有在线被控端已执行最小化", foreground="green")
        except Exception as e:
            # 异常全捕获，UI提示错误
            self.status_label.config(text=f"状态：发送失败！错误原因：{str(e)}", foreground="red")
        finally:
            # 2秒后恢复按钮可用状态和就绪提示（如果未置顶）
            self.root.after(2000, self.reset_status)

    # 重置状态和按钮
    def reset_status(self):
        self.send_btn.config(state="normal")
        # 只有未置顶时才恢复默认提示，置顶状态保留置顶提示
        if not self.always_on_top:
            self.status_label.config(
                text="状态：就绪，确保和被控端在同一局域网、端口一致",
                foreground="gray"
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = ControllerApp(root)
    root.mainloop()