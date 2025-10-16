import win32gui
import win32api
import win32con
import time
import ctypes
import sys
import threading
import tkinter as tk
from tkinter import ttk

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

# ============ 全局变量 ============
stop_flag = False
canvas_info = None
debug_gui = None

# ============ GUI调试窗口 ============
class DebugGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("心动小镇绘画调试器")
        self.root.geometry("400x550+50+50")
        self.root.attributes('-topmost', True)  # 窗口置顶
        
        # 状态区
        status_frame = ttk.LabelFrame(self.root, text="状态", padding=10)
        status_frame.pack(fill='x', padx=10, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="等待开始...", 
                                      font=('Arial', 10, 'bold'))
        self.status_label.pack()
        
        # 窗口信息区
        window_frame = ttk.LabelFrame(self.root, text="窗口信息", padding=10)
        window_frame.pack(fill='x', padx=10, pady=5)
        
        self.window_info = tk.Text(window_frame, height=3, width=45)
        self.window_info.pack()
        
        # 画板信息区
        canvas_frame = ttk.LabelFrame(self.root, text="画板信息", padding=10)
        canvas_frame.pack(fill='x', padx=10, pady=5)
        
        self.canvas_info_text = tk.Text(canvas_frame, height=6, width=45)
        self.canvas_info_text.pack()
        
        # 校准参数区
        param_frame = ttk.LabelFrame(self.root, text="校准参数（手动调整）", padding=10)
        param_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(param_frame, text="X偏移:").grid(row=0, column=0, sticky='w')
        self.offset_x = tk.IntVar(value=0)
        ttk.Entry(param_frame, textvariable=self.offset_x, width=10).grid(row=0, column=1)
        
        ttk.Label(param_frame, text="Y偏移:").grid(row=1, column=0, sticky='w')
        self.offset_y = tk.IntVar(value=0)
        ttk.Entry(param_frame, textvariable=self.offset_y, width=10).grid(row=1, column=1)
        
        ttk.Label(param_frame, text="画板大小:").grid(row=2, column=0, sticky='w')
        self.canvas_size = tk.IntVar(value=150)
        ttk.Entry(param_frame, textvariable=self.canvas_size, width=10).grid(row=2, column=1)
        
        # 控制按钮区
        button_frame = ttk.Frame(self.root, padding=10)
        button_frame.pack(fill='x', padx=10, pady=5)
        
        self.start_btn = ttk.Button(button_frame, text="开始校准", 
                                     command=self.start_calibration)
        self.start_btn.pack(side='left', padx=5)
        
        self.draw_btn = ttk.Button(button_frame, text="开始绘制", 
                                    command=self.start_drawing, state='disabled')
        self.draw_btn.pack(side='left', padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="停止", 
                                    command=self.stop_operation)
        self.stop_btn.pack(side='left', padx=5)
        
        # 日志区
        log_frame = ttk.LabelFrame(self.root, text="操作日志", padding=10)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(log_frame, height=8, width=45)
        self.log_text.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.log_text.config(yscrollcommand=scrollbar.set)
        
    def log(self, message):
        self.log_text.insert('end', f"{message}\n")
        self.log_text.see('end')
        self.root.update()
    
    def update_status(self, text):
        self.status_label.config(text=text)
        self.root.update()
    
    def update_window_info(self, text):
        self.window_info.delete('1.0', 'end')
        self.window_info.insert('1.0', text)
        self.root.update()
    
    def update_canvas_info(self, text):
        self.canvas_info_text.delete('1.0', 'end')
        self.canvas_info_text.insert('1.0', text)
        self.root.update()
    
    def start_calibration(self):
        threading.Thread(target=calibration_process, daemon=True).start()
    
    def start_drawing(self):
        threading.Thread(target=drawing_process, daemon=True).start()
    
    def stop_operation(self):
        global stop_flag
        stop_flag = True
        self.log("用户停止操作")
    
    def run(self):
        self.root.mainloop()

# ============ ESC键监听 ============
def check_esc_key():
    global stop_flag
    while not stop_flag:
        if win32api.GetAsyncKeyState(0x1B) & 0x8000:
            debug_gui.log("检测到ESC键")
            stop_flag = True
            break
        time.sleep(0.1)

# ============ 游戏窗口查找 ============
def find_game_window():
    hwnd = win32gui.FindWindow(None, "心动小镇")
    if not hwnd:
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if "心动" in title or "TapTap" in title:
                    windows.append((hwnd, title))
        windows = []
        win32gui.EnumWindows(callback, windows)
        if windows:
            hwnd = windows[0][0]
    return hwnd

# ============ 点击函数 ============
def click_at(x, y):
    if stop_flag:
        return False
    win32api.SetCursorPos((x, y))
    time.sleep(0.01)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.01)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    return True

# ============ 校准流程 ============
def calibration_process():
    global canvas_info, stop_flag
    stop_flag = False
    
    debug_gui.update_status("正在校准...")
    debug_gui.start_btn.config(state='disabled')
    
    hwnd = find_game_window()
    if not hwnd:
        debug_gui.log("❌ 未找到游戏窗口")
        debug_gui.start_btn.config(state='normal')
        return
    
    rect = win32gui.GetWindowRect(hwnd)
    window_center_x = (rect[0] + rect[2]) // 2
    window_center_y = (rect[1] + rect[3]) // 2
    
    debug_gui.update_window_info(
        f"窗口标题: {win32gui.GetWindowText(hwnd)}\n"
        f"窗口范围: ({rect[0]}, {rect[1]}) - ({rect[2]}, {rect[3]})\n"
        f"窗口中心: ({window_center_x}, {window_center_y})"
    )
    
    # 获取用户设置的参数
    offset_x = debug_gui.offset_x.get()
    offset_y = debug_gui.offset_y.get()
    canvas_size = debug_gui.canvas_size.get()
    
    # 计算画板范围
    canvas_center_x = window_center_x + offset_x
    canvas_center_y = window_center_y + offset_y
    half_size = canvas_size // 2
    
    canvas_info = {
        'left': canvas_center_x - half_size,
        'top': canvas_center_y - half_size,
        'right': canvas_center_x + half_size,
        'bottom': canvas_center_y + half_size,
        'center_x': canvas_center_x,
        'center_y': canvas_center_y,
        'width': canvas_size,
        'height': canvas_size
    }
    
    debug_gui.update_canvas_info(
        f"画板中心: ({canvas_center_x}, {canvas_center_y})\n"
        f"画板范围:\n"
        f"  左: {canvas_info['left']}\n"
        f"  上: {canvas_info['top']}\n"
        f"  右: {canvas_info['right']}\n"
        f"  下: {canvas_info['bottom']}"
    )
    
    # 标记四个角
    debug_gui.log("标记画板四个角...")
    click_at(canvas_info['left'], canvas_info['top'])
    time.sleep(0.3)
    click_at(canvas_info['right'], canvas_info['top'])
    time.sleep(0.3)
    click_at(canvas_info['right'], canvas_info['bottom'])
    time.sleep(0.3)
    click_at(canvas_info['left'], canvas_info['bottom'])
    time.sleep(0.3)
    
    # 标记中心
    debug_gui.log("标记画板中心...")
    click_at(canvas_center_x, canvas_center_y)
    
    debug_gui.log("✅ 校准完成！请检查游戏中的标记点")
    debug_gui.log("如果不准确，调整偏移参数后重新校准")
    debug_gui.update_status("校准完成")
    debug_gui.start_btn.config(state='normal')
    debug_gui.draw_btn.config(state='normal')

# ============ 绘制流程 ============
def drawing_process():
    global stop_flag
    
    if not canvas_info:
        debug_gui.log("❌ 请先进行校准")
        return
    
    stop_flag = False
    debug_gui.update_status("正在绘制...")
    debug_gui.draw_btn.config(state='disabled')
    
    cx = canvas_info['center_x']
    cy = canvas_info['center_y']
    left = canvas_info['left']
    top = canvas_info['top']
    right = canvas_info['right']
    bottom = canvas_info['bottom']
    
    # 画中心十字线
    debug_gui.log("绘制水平十字线...")
    for x in range(left, right + 1, 2):
        if stop_flag:
            break
        click_at(x, cy)
        time.sleep(0.005)
    
    debug_gui.log("绘制垂直十字线...")
    for y in range(top, bottom + 1, 2):
        if stop_flag:
            break
        click_at(cx, y)
        time.sleep(0.005)
    
    # 画四角正方形
    corner_offset = 15
    square_size = 8
    corners = [
        (left + corner_offset, top + corner_offset, "左上"),
        (right - corner_offset, top + corner_offset, "右上"),
        (left + corner_offset, bottom - corner_offset, "左下"),
        (right - corner_offset, bottom - corner_offset, "右下")
    ]
    
    for cx_corner, cy_corner, name in corners:
        if stop_flag:
            break
        debug_gui.log(f"绘制{name}角正方形...")
        
        square_points = [
            (cx_corner - square_size, cy_corner - square_size),
            (cx_corner + square_size, cy_corner - square_size),
            (cx_corner + square_size, cy_corner + square_size),
            (cx_corner - square_size, cy_corner + square_size)
        ]
        
        for i in range(4):
            if stop_flag:
                break
            start = square_points[i]
            end = square_points[(i + 1) % 4]
            steps = max(abs(end[0] - start[0]), abs(end[1] - start[1]))
            
            for step in range(steps + 1):
                if stop_flag:
                    break
                t = step / max(steps, 1)
                x = int(start[0] + (end[0] - start[0]) * t)
                y = int(start[1] + (end[1] - start[1]) * t)
                click_at(x, y)
                time.sleep(0.005)
    
    if stop_flag:
        debug_gui.log("❌ 绘制已中断")
        debug_gui.update_status("已停止")
    else:
        debug_gui.log("✅ 绘制完成")
        debug_gui.update_status("绘制完成")
    
    debug_gui.draw_btn.config(state='normal')

# ============ 主程序 ============
if __name__ == "__main__":
    run_as_admin()
    
    # 创建GUI
    debug_gui = DebugGUI()
    
    # 启动ESC监听
    esc_thread = threading.Thread(target=check_esc_key, daemon=True)
    esc_thread.start()
    
    debug_gui.log("程序已启动")
    debug_gui.log("按ESC可随时停止")
    
    # 运行GUI
    debug_gui.run()
