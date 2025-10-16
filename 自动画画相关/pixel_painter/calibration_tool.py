"""
交互式校准工具 - 用于精确确定画板坐标
"""
import win32gui
import win32api
import win32con
import tkinter as tk
from tkinter import ttk
import time
import threading
import ctypes
import sys

# ============ 管理员权限处理 ============
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable,
            " ".join([f'"{arg}"' for arg in sys.argv]),
            None, 1
        )
        sys.exit()

class CalibrationTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("画板坐标校准工具")
        self.root.geometry("450x700")
        self.root.attributes('-topmost', True)
        
        # 窗口信息
        self.target_hwnd = None
        self.window_rect = None
        
        # 画板信息（从你的参考数据）
        self.canvas_left = 544
        self.canvas_top = 277
        self.canvas_right = 1126
        self.canvas_bottom = 859
        
        self.create_widgets()
    
    def create_widgets(self):
        # 窗口选择区
        win_frame = ttk.LabelFrame(self.root, text="1. 选择目标窗口", padding=10)
        win_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(win_frame, text="选择前景窗口", 
                  command=self.select_foreground_window).pack(side='left', padx=5)
        
        self.win_label = ttk.Label(win_frame, text="未选择", foreground="gray")
        self.win_label.pack(side='left', padx=10)
        
        # 窗口信息显示
        info_frame = ttk.LabelFrame(self.root, text="窗口信息", padding=10)
        info_frame.pack(fill='x', padx=10, pady=5)
        
        self.win_info_text = tk.Text(info_frame, height=4, width=50)
        self.win_info_text.pack()
        
        # 画板坐标调整区
        canvas_frame = ttk.LabelFrame(self.root, text="2. 调整画板坐标", padding=10)
        canvas_frame.pack(fill='x', padx=10, pady=5)
        
        # 左边界
        ttk.Label(canvas_frame, text="左边界 (X):").grid(row=0, column=0, sticky='w', pady=2)
        self.left_var = tk.IntVar(value=self.canvas_left)
        ttk.Entry(canvas_frame, textvariable=self.left_var, width=10).grid(row=0, column=1, padx=5)
        ttk.Button(canvas_frame, text="-10", command=lambda: self.adjust('left', -10), width=5).grid(row=0, column=2)
        ttk.Button(canvas_frame, text="+10", command=lambda: self.adjust('left', 10), width=5).grid(row=0, column=3)
        
        # 上边界
        ttk.Label(canvas_frame, text="上边界 (Y):").grid(row=1, column=0, sticky='w', pady=2)
        self.top_var = tk.IntVar(value=self.canvas_top)
        ttk.Entry(canvas_frame, textvariable=self.top_var, width=10).grid(row=1, column=1, padx=5)
        ttk.Button(canvas_frame, text="-10", command=lambda: self.adjust('top', -10), width=5).grid(row=1, column=2)
        ttk.Button(canvas_frame, text="+10", command=lambda: self.adjust('top', 10), width=5).grid(row=1, column=3)
        
        # 右边界
        ttk.Label(canvas_frame, text="右边界 (X):").grid(row=2, column=0, sticky='w', pady=2)
        self.right_var = tk.IntVar(value=self.canvas_right)
        ttk.Entry(canvas_frame, textvariable=self.right_var, width=10).grid(row=2, column=1, padx=5)
        ttk.Button(canvas_frame, text="-10", command=lambda: self.adjust('right', -10), width=5).grid(row=2, column=2)
        ttk.Button(canvas_frame, text="+10", command=lambda: self.adjust('right', 10), width=5).grid(row=2, column=3)
        
        # 下边界
        ttk.Label(canvas_frame, text="下边界 (Y):").grid(row=3, column=0, sticky='w', pady=2)
        self.bottom_var = tk.IntVar(value=self.canvas_bottom)
        ttk.Entry(canvas_frame, textvariable=self.bottom_var, width=10).grid(row=3, column=1, padx=5)
        ttk.Button(canvas_frame, text="-10", command=lambda: self.adjust('bottom', -10), width=5).grid(row=3, column=2)
        ttk.Button(canvas_frame, text="+10", command=lambda: self.adjust('bottom', 10), width=5).grid(row=3, column=3)
        
        # 画板信息显示
        self.canvas_info = ttk.Label(canvas_frame, text="", foreground="blue")
        self.canvas_info.grid(row=4, column=0, columnspan=4, pady=10)
        self.update_canvas_info()
        
        # 测试区
        test_frame = ttk.LabelFrame(self.root, text="3. 测试标记", padding=10)
        test_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(test_frame, text="将在画板上标记5个点（中心+四角）", 
                 foreground="blue").pack(pady=5)
        
        ttk.Button(test_frame, text="开始测试标记", 
                  command=self.test_mark, width=20).pack(pady=5)
        
        self.test_status = ttk.Label(test_frame, text="未测试", foreground="gray")
        self.test_status.pack(pady=5)
        
        # 导出区
        export_frame = ttk.LabelFrame(self.root, text="4. 导出配置", padding=10)
        export_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(export_frame, text="复制坐标配置", 
                  command=self.export_config, width=20).pack(pady=5)
        
        # 日志区
        log_frame = ttk.LabelFrame(self.root, text="操作日志", padding=10)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(log_frame, height=10, width=50)
        self.log_text.pack(fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.log_text.config(yscrollcommand=scrollbar.set)
    
    def log(self, message):
        """添加日志"""
        self.log_text.insert('end', f"{message}\n")
        self.log_text.see('end')
        self.root.update()
    
    def select_foreground_window(self):
        """选择前景窗口"""
        self.log("请在3秒内切换到目标窗口...")
        self.root.update()
        time.sleep(3)
        
        self.target_hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(self.target_hwnd)
        self.window_rect = win32gui.GetWindowRect(self.target_hwnd)
        
        self.win_label.config(text=f"{title[:30]}", foreground="green")
        self.log(f"✓ 已选择窗口: {title}")
        
        # 显示窗口信息
        left, top, right, bottom = self.window_rect
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        
        info = (f"窗口: {title}\n"
               f"位置: ({left}, {top}) - ({right}, {bottom})\n"
               f"大小: {right-left} x {bottom-top}\n"
               f"中心: ({center_x}, {center_y})")
        
        self.win_info_text.delete('1.0', 'end')
        self.win_info_text.insert('1.0', info)
    
    def adjust(self, edge, delta):
        """调整边界值"""
        if edge == 'left':
            self.left_var.set(self.left_var.get() + delta)
        elif edge == 'top':
            self.top_var.set(self.top_var.get() + delta)
        elif edge == 'right':
            self.right_var.set(self.right_var.get() + delta)
        elif edge == 'bottom':
            self.bottom_var.set(self.bottom_var.get() + delta)
        
        self.update_canvas_info()
    
    def update_canvas_info(self):
        """更新画板信息显示"""
        left = self.left_var.get()
        top = self.top_var.get()
        right = self.right_var.get()
        bottom = self.bottom_var.get()
        
        width = right - left
        height = bottom - top
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        
        info = f"宽度: {width}, 高度: {height}, 中心: ({center_x}, {center_y})"
        self.canvas_info.config(text=info)
    
    def test_mark(self):
        """测试标记"""
        if not self.target_hwnd:
            self.log("❌ 请先选择窗口")
            return
        
        self.test_status.config(text="测试中...", foreground="orange")
        threading.Thread(target=self._do_test_mark, daemon=True).start()
    
    def _do_test_mark(self):
        """执行测试标记"""
        left = self.left_var.get()
        top = self.top_var.get()
        right = self.right_var.get()
        bottom = self.bottom_var.get()
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        
        points = [
            (center_x, center_y, "中心"),
            (left, top, "左上角"),
            (right, top, "右上角"),
            (left, bottom, "左下角"),
            (right, bottom, "右下角")
        ]
        
        self.log("\n开始标记测试点...")
        
        for x, y, name in points:
            self.log(f"  标记 {name}: ({x}, {y})")
            
            # 聚焦窗口
            win32gui.SetForegroundWindow(self.target_hwnd)
            time.sleep(0.1)
            
            # 点击
            win32api.SetCursorPos((x, y))
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.3)
        
        self.log("✓ 测试完成 - 检查游戏中的5个标记点")
        self.root.after(0, lambda: self.test_status.config(
            text="测试完成 ✓", foreground="green"))
    
    def export_config(self):
        """导出配置"""
        left = self.left_var.get()
        top = self.top_var.get()
        right = self.right_var.get()
        bottom = self.bottom_var.get()
        
        config = f"""
# 画板校准配置
画板坐标:
  左上角: ({left}, {top})
  右下角: ({right}, {bottom})
  宽度: {right - left}
  高度: {bottom - top}
  中心: ({(left+right)//2}, {(top+bottom)//2})

在 painter.py 中使用:
self.grid_start = ({left}, {top})
self.grid_end = ({right}, {bottom})
"""
        
        self.root.clipboard_clear()
        self.root.clipboard_append(config)
        self.log("✓ 配置已复制到剪贴板")
        self.log(config)
    
    def run(self):
        """运行GUI"""
        self.log("校准工具已启动")
        self.log("步骤:")
        self.log("1. 点击'选择前景窗口'并切换到游戏窗口")
        self.log("2. 调整画板边界坐标")
        self.log("3. 点击'开始测试标记'验证坐标")
        self.log("4. 重复2-3直到5个点完全准确")
        self.log("5. 点击'复制坐标配置'保存结果")
        self.root.mainloop()

if __name__ == "__main__":
    tool = CalibrationTool()
    tool.run()
