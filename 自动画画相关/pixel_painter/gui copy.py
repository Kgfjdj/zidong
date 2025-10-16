import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import json
import time
import threading
from painter import PixelPainter
from pynput import mouse, keyboard
import win32gui
import win32api
import win32con
from win_input import win_input

class PixelPainterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("像素画自动填充工具")
        self.root.geometry("400x900")
        
        # 设置窗口置顶
        self.root.attributes('-topmost', True)

        self.painter = PixelPainter()
        self.json_data = None
        self.calibration_mode = None
        self.calibration_points = []
        
        # 坐标记录相关变量
        self.temp_coords = []
        self.is_tracking = False
        self.current_mouse_pos = (0, 0)
        
        # 绘制状态标志
        self.is_painting = False
        
        # 绘制起始坐标
        self.start_x = 0
        self.start_y = 0
        
        self.create_widgets()
        self.auto_select_window()  # 自动选择窗口
        self.load_saved_config()
        
        # 启动鼠标位置监听
        self.mouse_listener = mouse.Listener(on_move=self.on_mouse_move)
        self.mouse_listener.start()
        
        # 启动键盘监听
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
        self.keyboard_listener.start()
    
    def auto_select_window(self):
        """自动选择心动小镇窗口"""
        hwnd = win32gui.FindWindow(None, "心动小镇")
        if not hwnd:
            # 模糊查找
            def callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if "心动" in title or "小镇" in title:
                        windows.append((hwnd, title))
            windows = []
            win32gui.EnumWindows(callback, windows)
            if windows:
                hwnd = windows[0][0]
        
        if hwnd:
            from win_input import win_input
            win_input.target_hwnd = hwnd
            window_title = win32gui.GetWindowText(hwnd)
            self.window_label.config(
                text=f"已选择: {window_title}", 
                fg="green"
            )
            self.log(f"✓ 自动选择窗口: {window_title}")
        else:
            self.window_label.config(
                text="未找到心动小镇窗口", 
                fg="red"
            )
            self.log("✗ 未找到心动小镇窗口，请手动选择")
    
    def create_widgets(self):
        """创建界面组件"""
        # 标题
        title = tk.Label(self.root, text="像素画自动填充工具", 
                         font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # 置顶控制和快捷键提示
        topmost_frame = tk.Frame(self.root)
        topmost_frame.pack(fill="x", padx=10, pady=5)
        
        self.topmost_var = tk.BooleanVar(value=True)
        tk.Checkbutton(topmost_frame, text="窗口置顶", 
                      variable=self.topmost_var,
                      command=self.toggle_topmost).pack(side="left")
        
        # 快捷键提示
        shortcut_text = "快捷键: P-开始 | O-暂停 | I-停止 | ESC-紧急停止 | Space-确认坐标"
        tk.Label(topmost_frame, text=shortcut_text, 
                fg="blue", font=("Arial", 9, "bold")).pack(side="right", padx=10)
        
        # 窗口选择区域
        window_frame = ttk.LabelFrame(self.root, text="0. 目标窗口", padding=10)
        window_frame.pack(fill="x", padx=10, pady=5)
        
        self.window_label = tk.Label(window_frame, text="未选择窗口", fg="gray")
        self.window_label.pack(side="left", padx=5)
        
        tk.Button(window_frame, text="重新选择", 
                command=self.auto_select_window).pack(side="right")
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(self.root, text="1. 加载像素画数据", padding=10)
        file_frame.pack(fill="x", padx=10, pady=5)
        
        self.file_label = tk.Label(file_frame, text="未选择文件", fg="gray")
        self.file_label.pack(side="left", padx=5)
        
        tk.Button(file_frame, text="选择JSON文件", 
                  command=self.load_json).pack(side="right")
        
        # 绘制起始坐标设置
        start_coord_frame = ttk.LabelFrame(self.root, text="2. 绘制起始坐标（像素画内坐标）", padding=10)
        start_coord_frame.pack(fill="x", padx=10, pady=5)
        
        coord_input_frame = tk.Frame(start_coord_frame)
        coord_input_frame.pack(fill="x", pady=5)
        
        tk.Label(coord_input_frame, text="起始X:").pack(side="left", padx=5)
        self.start_x_entry = tk.Entry(coord_input_frame, width=8)
        self.start_x_entry.insert(0, "0")
        self.start_x_entry.pack(side="left", padx=5)
        
        tk.Label(coord_input_frame, text="起始Y:").pack(side="left", padx=5)
        self.start_y_entry = tk.Entry(coord_input_frame, width=8)
        self.start_y_entry.insert(0, "0")
        self.start_y_entry.pack(side="left", padx=5)
        
        tk.Label(coord_input_frame, text="（将绘制150×150区域）", 
                fg="blue").pack(side="left", padx=10)
        
        # 校准区域
        calib_frame = ttk.LabelFrame(self.root, text="3. 画板坐标校准", padding=10)
        calib_frame.pack(fill="x", padx=10, pady=5)
        
        # 画板校准
        grid_frame = tk.Frame(calib_frame)
        grid_frame.pack(fill="x", pady=5)
        
        tk.Label(grid_frame, text="画板校准:").pack(side="left")
        tk.Button(grid_frame, text="标记左上角", 
                  command=lambda: self.start_calibration("grid_start")).pack(side="left", padx=5)
        tk.Button(grid_frame, text="标记右下角", 
                  command=lambda: self.start_calibration("grid_end")).pack(side="left", padx=5)
        
        self.grid_status = tk.Label(grid_frame, text="未校准", fg="red")
        self.grid_status.pack(side="left", padx=10)
        
        # 坐标选取控制区域
        coord_control_frame = ttk.LabelFrame(self.root, text="坐标选取", padding=10)
        coord_control_frame.pack(fill="x", padx=10, pady=5)
        
        # 坐标显示
        self.coord_label = tk.Label(coord_control_frame, 
                                     text="当前坐标: X: 0, Y: 0", 
                                     font=("Arial", 11))
        self.coord_label.pack(pady=5)
        
        # 控制按钮
        coord_btn_frame = tk.Frame(coord_control_frame)
        coord_btn_frame.pack(pady=5)
        
        self.track_btn = tk.Button(coord_btn_frame, text="开始追踪光标", 
                                   command=self.toggle_tracking,
                                   bg="#2196F3", fg="white", width=12)
        self.track_btn.pack(side="left", padx=5)
        
        self.confirm_button = tk.Button(coord_btn_frame, text="取消追踪",
                                        command=self.cancel_coordinates,
                                        state="disabled", bg="#4CAF50", fg="white", width=12)
        self.confirm_button.pack(side="left", padx=5)
        
        self.cancel_button = tk.Button(coord_btn_frame, text="重置",
                                       command=self.cancel_coordinates,
                                       state="disabled", width=12)
        self.cancel_button.pack(side="left", padx=5)
        
        # 提示信息
        tip_label = tk.Label(coord_control_frame, 
                            text="提示:点击'开始追踪光标'后移动鼠标到目标位置,然后按'Space'键确认坐标",
                            font=("Arial", 9), fg="blue")
        tip_label.pack(pady=5)
        
        # 控制区域
        control_frame = ttk.LabelFrame(self.root, text="4. 控制面板", padding=10)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        btn_frame = tk.Frame(control_frame)
        btn_frame.pack()
        
        self.start_btn = tk.Button(btn_frame, text="开始绘制 (P)", 
                                    command=self.start_painting, 
                                    bg="#4CAF50", fg="white", 
                                    width=15, height=2)
        self.start_btn.pack(side="left", padx=5)
        
        self.pause_btn = tk.Button(btn_frame, text="暂停 (O)", 
                                    command=self.pause_painting, 
                                    bg="#FF9800", fg="white", 
                                    width=15, height=2, state="disabled")
        self.pause_btn.pack(side="left", padx=5)
        
        self.stop_btn = tk.Button(btn_frame, text="停止 (I)", 
                                   command=self.stop_painting, 
                                   bg="#f44336", fg="white", 
                                   width=15, height=2, state="disabled")
        self.stop_btn.pack(side="left", padx=5)
        
        # 进度区域
        progress_frame = ttk.LabelFrame(self.root, text="进度", padding=10)
        progress_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill="x", pady=5)
        
        self.progress_label = tk.Label(progress_frame, text="等待开始...", 
                                        font=("Arial", 10))
        self.progress_label.pack()
        
        # 日志区域
        log_frame = ttk.LabelFrame(self.root, text="日志", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(log_frame, height=6, state="disabled")
        self.log_text.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(self.log_text)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)
    
    def on_key_press(self, key):
        """键盘按键事件监听"""
        try:
            # P键 - 开始绘制
            if hasattr(key, 'char') and key.char and key.char.lower() == 'p':
                if not self.is_painting and self.start_btn['state'] == 'normal':
                    self.root.after(0, self.start_painting)
                    self.root.after(0, lambda: self.log("⌨️ 按下 P 键 - 开始绘制"))
            
            # O键 - 暂停/恢复
            elif hasattr(key, 'char') and key.char and key.char.lower() == 'o':
                if self.is_painting and self.pause_btn['state'] == 'normal':
                    self.root.after(0, self.pause_painting)
                    if self.painter.is_paused:
                        self.root.after(0, lambda: self.log("⌨️ 按下 O 键 - 已暂停"))
                    else:
                        self.root.after(0, lambda: self.log("⌨️ 按下 O 键 - 已恢复"))
            
            # I键 - 停止
            elif hasattr(key, 'char') and key.char and key.char.lower() == 'i':
                if self.is_painting and self.stop_btn['state'] == 'normal':
                    self.root.after(0, self.stop_painting)
                    self.root.after(0, lambda: self.log("⌨️ 按下 I 键 - 停止绘制"))
            
            # ESC键 - 紧急停止
            elif key == keyboard.Key.esc:
                if self.is_painting:
                    self.root.after(0, self.emergency_stop)
            
            # Space键 - 确认坐标
            elif key == keyboard.Key.space and self.is_tracking:
                if self.calibration_mode:
                    self.root.after(0, lambda: self._perform_confirmation_action(
                        self.current_mouse_pos[0], 
                        self.current_mouse_pos[1], 
                        source="keyboard"
                    ))
                    self.root.after(0, lambda: self.log("⌨️ 按下 Space 键 - 确认坐标"))
                else:
                    self.root.after(0, lambda: self.log("按键确认被忽略: 未处于校准模式"))
        
        except AttributeError:
            pass
    
    def emergency_stop(self):
        """紧急停止(ESC键触发)"""
        self.log("⚠️ 检测到 ESC 键,紧急停止绘制!")
        self.stop_painting()
        messagebox.showinfo("已停止", "绘制已通过 ESC 键紧急停止")
    
    def toggle_topmost(self):
        """切换窗口置顶状态"""
        self.root.attributes('-topmost', self.topmost_var.get())
    
    def on_mouse_move(self, x, y):
        """鼠标移动事件监听"""
        self.current_mouse_pos = (x, y)
        if self.is_tracking:
            self.root.after(0, lambda: self.coord_label.config(
                text=f"当前坐标: X: {x}, Y: {y}"
            ))
    
    def toggle_tracking(self):
        """开始/停止追踪光标"""
        if not self.is_tracking:
            # 开始追踪
            self.is_tracking = True
            self.track_btn.config(text="停止追踪", bg="#FF5722")
            self.confirm_button.config(state="normal")
            self.cancel_button.config(state="normal")
            self.log("开始追踪光标位置...请移动鼠标到目标位置，然后按 'Space' 键确认。")
        else:
            # 停止追踪
            self.cancel_coordinates()
            self.log("停止追踪光标")
    
    def _save_confirmed_coordinate(self, x, y):
        """保存确认的坐标"""
        # 转换为客户端坐标
        from win_input import win_input
        if win_input.target_hwnd:
            client_x, client_y = win_input.screen_to_client(win_input.target_hwnd, x, y)
        else:
            client_x, client_y = x, y
        
        if self.calibration_mode == "grid_start":
            self.painter.grid_start = (client_x, client_y)
            self.log(f"✓ 画板左上角（客户端坐标）: ({client_x}, {client_y})")
            self.check_grid_calibration()
        
        elif self.calibration_mode == "grid_end":
            self.painter.grid_end = (client_x, client_y)
            self.log(f"✓ 画板右下角（客户端坐标）: ({client_x}, {client_y})")
            self.check_grid_calibration()
        
        self.painter.save_config()
    
    def _perform_confirmation_action(self, x, y, source="keyboard"):
        """执行坐标确认的动作"""
        if not self.is_tracking:
            self.log("未处于追踪模式，无法确认坐标。")
            return

        if self.calibration_mode:
            self._save_confirmed_coordinate(x, y)
            
            # 重置状态
            self.is_tracking = False
            self.track_btn.config(text="开始追踪光标", bg="#2196F3")
            self.confirm_button.config(state="disabled")
            self.cancel_button.config(state="disabled")
            self.coord_label.config(text=f"已确认坐标: X: {x}, Y: {y}")
            self.calibration_mode = None
        else:
            self.log("未选择校准模式，无法确认坐标。")

    def cancel_coordinates(self):
        """取消坐标选择或重置追踪状态"""
        self.is_tracking = False
        self.track_btn.config(text="开始追踪光标", bg="#2196F3")
        self.confirm_button.config(state="disabled")
        self.cancel_button.config(state="disabled")
        self.coord_label.config(text="当前坐标: X: 0, Y: 0")
        self.calibration_mode = None
        self.log("已取消坐标选择/追踪")
    
    def start_calibration(self, mode):
        """开始坐标校准"""
        self.calibration_mode = mode
        mode_names = {
            "grid_start": "画板左上角（150×150格子的左上角）",
            "grid_end": "画板右下角（150×150格子的右下角）"
        }
        self.log(f"请移动光标到 {mode_names.get(mode, mode)} 的位置,然后按'Space'键确认坐标")
        
        # 自动开始追踪
        if not self.is_tracking:
            self.toggle_tracking()
    
    def check_grid_calibration(self):
        """检查画板校准状态"""
        if self.painter.grid_start and self.painter.grid_end:
            self.grid_status.config(text="已校准 ✓", fg="green")
    
    def load_saved_config(self):
        """加载保存的配置"""
        if self.painter.config:
            if self.painter.config.get("grid_start"):
                self.painter.grid_start = tuple(self.painter.config["grid_start"])
            if self.painter.config.get("grid_end"):
                self.painter.grid_end = tuple(self.painter.config["grid_end"])
            
            self.check_grid_calibration()
            self.log("✓ 已加载保存的坐标配置")
    
    def log(self, message):
        """添加日志"""
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
    
    def load_json(self):
        """加载JSON文件"""
        filename = filedialog.askopenfilename(
            title="选择像素画JSON文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    self.json_data = json.load(f)
                
                width = self.json_data['width']
                height = self.json_data['height']
                
                self.file_label.config(
                    text=f"{filename.split('/')[-1]} ({width}×{height})", 
                    fg="green"
                )
                self.log(f"✓ 已加载: {filename}")
                self.log(f"  原始尺寸: {width}×{height}")
                self.log(f"  将绘制区域: 150×150（可通过起始坐标选择）")
            
            except Exception as e:
                messagebox.showerror("错误", f"加载文件失败:\n{str(e)}")
                self.log(f"✗ 加载失败: {str(e)}")
    
    def start_painting(self):
        """开始绘制"""
        if not self.json_data:
            messagebox.showwarning("警告", "请先加载JSON文件")
            return
        
        if not self.painter.grid_start or not self.painter.grid_end:
            messagebox.showwarning("警告", "请先完成画板校准")
            return
        
        # 获取起始坐标
        try:
            self.start_x = int(self.start_x_entry.get())
            self.start_y = int(self.start_y_entry.get())
        except ValueError:
            messagebox.showerror("错误", "起始坐标必须是整数")
            return
        
        # 检查坐标范围
        max_x = self.json_data['width'] - 150
        max_y = self.json_data['height'] - 150
        
        if self.start_x < 0 or self.start_x > max_x:
            messagebox.showerror("错误", f"起始X坐标范围: 0-{max_x}")
            return
        
        if self.start_y < 0 or self.start_y > max_y:
            messagebox.showerror("错误", f"起始Y坐标范围: 0-{max_y}")
            return
        
        self.is_painting = True
        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="normal")
        self.stop_btn.config(state="normal")
        
        self.log("========== 开始绘制 ==========")
        self.log(f"绘制区域: [{self.start_x}, {self.start_y}] 到 [{self.start_x+149}, {self.start_y+149}]")
        self.log("💡 快捷键: P-开始 | O-暂停 | I-停止 | ESC-紧急停止")
        
        # 在新线程中执行绘制
        def paint_thread():
            try:
                # 添加3秒倒计时
                for i in range(3, 0, -1):
                    if not self.is_painting:
                        return
                    self.root.after(0, lambda sec=i: self.log(f"⏳ {sec}秒后开始绘制..."))
                    time.sleep(1)
                
                self.root.after(0, lambda: self.log("🚀 正式开始绘制!"))
                
                # 提取150×150的区域
                cropped_data = self.extract_region(
                    self.json_data, 
                    self.start_x, 
                    self.start_y, 
                    150, 
                    150
                )
                
                self.painter.paint_from_json(cropped_data, self.update_progress)
                self.root.after(0, self.painting_finished)
            except Exception as e:
                self.root.after(0, lambda: self.painting_error(str(e)))
        
        threading.Thread(target=paint_thread, daemon=True).start()
    
    def extract_region(self, json_data, start_x, start_y, width, height):
        """从大图中提取指定区域"""
        pixels = json_data['pixels']
        cropped_pixels = []
        
        for y in range(start_y, start_y + height):
            row = []
            for x in range(start_x, start_x + width):
                row.append(pixels[y][x])
            cropped_pixels.append(row)
        
        return {
            "width": width,
            "height": height,
            "pixels": cropped_pixels
        }

    def pause_painting(self):
        """暂停/恢复绘制"""
        if self.painter.is_paused:
            self.painter.resume()
            self.pause_btn.config(text="暂停 (O)")
            self.log("▶ 已恢复")
        else:
            self.painter.pause()
            self.pause_btn.config(text="继续 (O)")
            self.log("⏸ 已暂停")
    
    def stop_painting(self):
        """停止绘制"""
        self.is_painting = False
        self.painter.stop()
        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self.log("⏹ 已停止")
    
    def update_progress(self, current, total, color):
        """更新进度"""
        progress = (current / total) * 100
        self.progress_bar['value'] = progress
        
        # 计算实际绘制的坐标
        actual_x = self.start_x + (current - 1) % 150
        actual_y = self.start_y + (current - 1) // 150
        
        self.progress_label.config(
            text=f"进度: {current}/{total} ({progress:.1f}%) | 当前位置: [{actual_x}, {actual_y}] | 颜色: {color}"
        )
    
    def painting_finished(self):
        """绘制完成"""
        self.is_painting = False
        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self.log("========== 绘制完成 ==========")
        messagebox.showinfo("完成", "像素画绘制完成!")
    
    def painting_error(self, error_msg):
        """绘制出错"""
        self.is_painting = False
        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self.log(f"✗ 错误: {error_msg}")
        messagebox.showerror("错误", f"绘制过程中出错:\n{error_msg}")

# def main():
#     root = tk.Tk()
#     app = PixelPainterGUI(root)
#     root.mainloop()

# if __name__ == "__main__":
#     main()
