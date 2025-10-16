import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import json
import time
import threading
from painter import PixelPainter
from pynput import mouse, keyboard
import win32gui # 假设您有这个模块来选择窗口
from win_input import win_input
import ctypes
import os

class PixelPainterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("像素画自动填充工具")
        self.root.geometry("400x900")
        
        # 设置窗口置顶
        self.root.attributes('-topmost', True)


        # 初始化所有变量（在 create_widgets 之前）
        self.painter = PixelPainter()
        self.json_data = None
        self.calibration_mode = None
        self.calibration_points = []
        # 起始颜色索引UAYH6 
        self.start_color_index = None
        self.start_color_spinbox = None
        self.total_colors_label = None
        
        # 坐标记录相关变量
        self.temp_coords = []
        self.is_tracking = False
        self.current_mouse_pos = (0, 0)
        
        # 绘制状态标志
        self.is_painting = False
        
        # 提前初始化 coord_label 为 None
        self.coord_label = None
        
        # 创建界面（这会真正创建 coord_label）
        self.create_widgets()

        # 设置窗口
        hwnd = self.find_game_window()
        print(hwnd)
        self.painter.set_window(hwnd)
        win_input.lock_window(hwnd)
                
        self.window_label.config(
            text=f"已锁定: 心动小镇", 
                fg="green"
        )
        self.log(f"✓ 已锁定窗口: 心动小镇")
        
        # 加载配置
        self.load_saved_config()

                # 启动键盘监听
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
        self.keyboard_listener.start()
        
        # 启动鼠标位置监听
        self.mouse_listener = mouse.Listener(on_move=self.on_mouse_move)
        self.mouse_listener.start()
        


        # 坐标记录相关变量
        self.temp_coords = []
        self.is_tracking = False
        self.current_mouse_pos = (0, 0)
        self.cursor_step = 5  # 方向键每次移动的像素数


    def create_widgets(self):
        """创建界面组件"""
        # 标题
        title = tk.Label(self.root, text="像素画自动填充工具", 
                         font=("Arial", 16, "bold"))
        title.pack(pady=10)



        # # 在 "控制区域" 之前添加
        # test_frame = ttk.LabelFrame(self.root, text="4. 测试模式", padding=10)
        # test_frame.pack(fill="x", padx=10, pady=5)

        # # 坐标测试
        # tk.Label(test_frame, text="坐标测试：加载JSON后点击测试，将在中心和四个角各点击一次", 
        #         font=("Arial", 9), fg="blue").pack(pady=5)

        # tk.Button(test_frame, text="开始坐标测试 (中心+四角)", 
        #         command=self.test_coordinates,
        #         bg="#9C27B0", fg="white", width=25).pack(pady=5)

        # self.test_info = tk.Label(test_frame, text="未运行", fg="gray")
        # self.test_info.pack(pady=5)
        
        # # 添加分隔线
        # ttk.Separator(test_frame, orient='horizontal').pack(fill='x', pady=10)
        
        # # 颜色选择测试
        # tk.Label(test_frame, text="颜色选择测试：输入多个颜色代码进行批量测试（用逗号分隔）", 
        #         font=("Arial", 9), fg="blue").pack(pady=5)
        
        # color_test_frame = tk.Frame(test_frame)
        # color_test_frame.pack(pady=5)
        
        # tk.Label(color_test_frame, text="颜色代码:").pack(side="left", padx=5)
        
        # # 使用Text控件代替Entry，支持多行输入
        # self.color_test_text = tk.Text(color_test_frame, width=40, height=3)
        # self.color_test_text.pack(side="left", padx=5)
        # self.color_test_text.insert("1.0", '["#753B31","#795126","#753B31"]')  # 默认示例
        
        # # 按钮框架
        # color_btn_frame = tk.Frame(test_frame)
        # color_btn_frame.pack(pady=5)
        
        # tk.Button(color_btn_frame, text="预览颜色列表", 
        #         command=self.preview_color_list,
        #         bg="#2196F3", fg="white", width=15).pack(side="left", padx=5)
        
        # tk.Button(color_btn_frame, text="✓ 确认并批量测试", 
        #         command=self.confirm_batch_color_test,
        #         bg="#4CAF50", fg="white", width=18).pack(side="left", padx=5)
        
        # tk.Button(color_btn_frame, text="清空", 
        #         command=lambda: self.color_test_text.delete("1.0", "end"),
        #         width=8).pack(side="left", padx=5)
        
        # self.color_test_info = tk.Label(test_frame, text="未测试", fg="gray")
        # self.color_test_info.pack(pady=5)
        
        # # 添加格式说明
        # format_label = tk.Label(test_frame, 
        #                     text='格式示例: ["#753B31","#795126","#753B31"] 或 753B31,795126,753B31', 
        #                     font=("Arial", 8), fg="gray")
        # format_label.pack(pady=2)

        # 置顶控制和快捷键提示
        topmost_frame = tk.Frame(self.root)
        topmost_frame.pack(fill="x", padx=10, pady=5)
        
        self.topmost_var = tk.BooleanVar(value=True)
        tk.Checkbutton(topmost_frame, text="窗口置顶", 
                      variable=self.topmost_var,
                      command=self.toggle_topmost).pack(side="left")
        
        # 快捷键提示
        shortcut_text = "快捷键: P-开始 | O-暂停 | I-停止 | ESC-紧急停止 | Space-确认坐标" # 添加Space键提示
        tk.Label(topmost_frame, text=shortcut_text, 
                fg="blue", font=("Arial", 9, "bold")).pack(side="right", padx=10)
        
        # 在文件选择区域之前添加窗口选择区域
        window_frame = ttk.LabelFrame(self.root, text="0. 目标窗口", padding=10)
        window_frame.pack(fill="x", padx=10, pady=5)
        
        self.window_label = tk.Label(window_frame, text="未选择窗口", fg="gray")
        self.window_label.pack(side="left", padx=5)
        
        tk.Button(window_frame, text="选择窗口", 
                command=self.select_target_window).pack(side="right")
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(self.root, text="1. 加载像素画数据", padding=10)
        file_frame.pack(fill="x", padx=10, pady=5)
        
        self.file_label = tk.Label(file_frame, text="未选择文件", fg="gray")
        self.file_label.pack(side="left", padx=5)
        
        tk.Button(file_frame, text="选择JSON文件", 
                  command=self.load_json).pack(side="right")
        
        # 校准区域
        calib_frame = ttk.LabelFrame(self.root, text="2. 坐标校准", padding=10)
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
        
        # 颜色选择器校准
        color_frame = tk.Frame(calib_frame)
        color_frame.pack(fill="x", pady=5)
        
        tk.Label(color_frame, text="颜色选择器:").pack(side="left")
        tk.Button(color_frame, text="标记左按钮", 
                  command=lambda: self.start_calibration("color_left")).pack(side="left", padx=5)
        tk.Button(color_frame, text="标记右按钮", 
                  command=lambda: self.start_calibration("color_right")).pack(side="left", padx=5)
        tk.Button(color_frame, text="标记颜色位置", 
                  command=self.calibrate_colors).pack(side="left", padx=5)
        
        self.color_status = tk.Label(color_frame, text="未校准", fg="red")
        self.color_status.pack(side="left", padx=10)
        
        # 坐标选取控制区域
        # coord_control_frame = ttk.LabelFrame(self.root, text="坐标选取", padding=5)
        # coord_control_frame.pack(fill="x", padx=10, pady=5)

        # 坐标显示
        # self.coord_label = tk.Label(coord_control_frame, 
        #                             text="当前坐标: X: 0, Y: 0", 
        #                             font=("Arial", 11))
        # self.coord_label.pack(pady=5)

        # 控制按钮
        # coord_btn_frame = tk.Frame(coord_control_frame)
        # coord_btn_frame.pack(pady=5)

        # self.track_btn = tk.Button(coord_btn_frame, text="开始校准", 
        #                         command=self.toggle_tracking,
        #                         bg="#2196F3", fg="white", width=12)
        # self.track_btn.pack(side="left", padx=5)

        # # 取消按钮
        # self.cancel_button = tk.Button(coord_btn_frame, text="取消", 
        #                             command=self.cancel_coordinates,
        #                             state="disabled", width=12)
        # self.cancel_button.pack(side="left", padx=5)

        # 提示信息 - 移除"点击"按钮，改为J键
        # tip_label = tk.Label(coord_control_frame, 
        #                     text="提示: 开始校准后用方向键移动光标，按'J'键双击当前位置，按'Space'键确认坐标", 
        #                     font=("Arial", 9), fg="blue", wraplength=380, justify="left")
        # tip_label.pack(pady=5)


        # ============ 在"控制面板"之前添加区域选择 ============
        region_frame = ttk.LabelFrame(self.root, text="2.5 区域选择（可选）", padding=10)
        region_frame.pack(fill="x", padx=10, pady=5)
        
        # 说明文本
        info_text = tk.Label(region_frame, 
                            text='输入起始坐标后自动绘制150×150区域，格式: [行, 列] 例如: [130, 400]',
                            font=("Arial", 9), fg="blue", wraplength=380, justify="left")
        info_text.pack(pady=5)
        
        # 坐标输入框
        coord_frame = tk.Frame(region_frame)
        coord_frame.pack(pady=5)
        
        tk.Label(coord_frame, text="起始坐标:").pack(side="left", padx=5)
        
        self.region_coord_var = tk.StringVar(value="")
        coord_entry = tk.Entry(coord_frame, textvariable=self.region_coord_var, width=15)
        coord_entry.pack(side="left", padx=5)
        
        # 区域大小（固定150×150，但可修改）
        tk.Label(coord_frame, text="区域大小:").pack(side="left", padx=10)
        
        self.region_size_var = tk.IntVar(value=150)
        tk.Spinbox(coord_frame, textvariable=self.region_size_var, 
                from_=10, to=1000, width=8).pack(side="left", padx=2)
        
        tk.Label(coord_frame, text="×").pack(side="left")
        tk.Label(coord_frame, textvariable=self.region_size_var, width=4).pack(side="left")
        
        # 按钮和状态
        btn_frame = tk.Frame(region_frame)
        btn_frame.pack(pady=5)
        
        tk.Button(btn_frame, text="验证", 
                command=self._validate_region,
                bg="#2196F3", fg="white", width=10).pack(side="left", padx=2)
        
        tk.Button(btn_frame, text="清空", 
                command=self._clear_region_selection,
                width=8).pack(side="left", padx=2)
        
        self.region_status_label = tk.Label(btn_frame, text="未选择区域（绘制全图）", fg="gray")
        self.region_status_label.pack(side="left", padx=10)
        
        # 示例提示
        example_label = tk.Label(region_frame, 
                                text='示例: [130,400] 或 [130, 400] 或 130,400', 
                                font=("Arial", 8), fg="gray")
        example_label.pack(pady=2)

        
        # ============ 控制区域 ============
        control_frame = ttk.LabelFrame(self.root, text="3. 控制面板", padding=10)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # 添加起始颜色选择
        start_color_frame = tk.Frame(control_frame)
        start_color_frame.pack(pady=5)
        
        tk.Label(start_color_frame, text="从第几个颜色开始绘制:").pack(side="left", padx=5)
        
        self.start_color_index = tk.IntVar(value=1)
        
        # ⚠️ 保存引用
        self.start_color_spinbox = tk.Spinbox(start_color_frame, 
                                            from_=1, 
                                            to=999, 
                                            textvariable=self.start_color_index,
                                            width=8)
        self.start_color_spinbox.pack(side="left", padx=5)
        
        tk.Label(start_color_frame, text="(1=从头开始)", 
                fg="gray", font=("Arial", 9)).pack(side="left", padx=5)
        
        # ⚠️ 保存引用
        self.total_colors_label = tk.Label(start_color_frame, 
                                        text="总颜色数: 未知", 
                                        fg="blue", font=("Arial", 9))
        self.total_colors_label.pack(side="left", padx=10)
        
        # 控制按钮
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

        # ✅ 修改进度标签为多行显示
        self.progress_label = tk.Label(progress_frame, text="等待开始...", 
                                        font=("Arial", 10), justify="left")
        self.progress_label.pack(pady=5)

        # ✅ 添加详细信息标签
        self.detail_label = tk.Label(progress_frame, text="", 
                                    font=("Arial", 9), fg="gray", justify="left")
        self.detail_label.pack()
        
        # 日志区域
        log_frame = ttk.LabelFrame(self.root, text="日志", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(log_frame, height=8, state="disabled")
        self.log_text.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(self.log_text)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)

    
    def _parse_coordinates(self, coord_str):
        """解析坐标字符串，支持多种格式
        
        支持格式:
        - [130, 400]
        - [130,400]
        - 130, 400
        - 130,400
        
        Returns:
            (row, col) 或 None
        """
        import re
        
        if not coord_str or not coord_str.strip():
            return None
        
        # 移除所有空格和方括号
        coord_str = coord_str.strip().replace('[', '').replace(']', '').replace(' ', '')
        
        # 用逗号分割
        parts = coord_str.split(',')
        
        if len(parts) != 2:
            raise ValueError("坐标格式错误，应该是两个数字，例如: [130, 400]")
        
        try:
            row = int(parts[0])
            col = int(parts[1])
            return (row, col)
        except ValueError:
            raise ValueError("坐标必须是整数")

    def _clear_region_selection(self):
        """清空区域选择"""
        self.region_coord_var.set("")
        self.region_status_label.config(text="未选择区域（绘制全图）", fg="gray")
        self.log("已清空区域选择")

    def _validate_region(self):
        """验证区域设置"""
        if not self.json_data:
            messagebox.showwarning("警告", "请先加载JSON文件")
            return
        
        try:
            region_info = self._get_region_info()
            
            if region_info is None:
                messagebox.showinfo("提示", "未设置区域，将绘制整张图片")
                self.region_status_label.config(text="未选择区域（绘制全图）", fg="gray")
                return
            
            start_row, start_col, region_size = region_info
            img_height = self.json_data['height']
            img_width = self.json_data['width']
            
            # 验证边界
            if start_row < 0 or start_col < 0:
                raise ValueError("起始坐标不能为负数")
            
            if start_row + region_size > img_height:
                raise ValueError(f"区域超出图片高度（{start_row + region_size} > {img_height}）")
            
            if start_col + region_size > img_width:
                raise ValueError(f"区域超出图片宽度（{start_col + region_size} > {img_width}）")
            
            # 显示成功信息
            info_msg = (f"✓ 区域设置有效\n\n"
                    f"起始位置: ({start_row}, {start_col})\n"
                    f"结束位置: ({start_row + region_size - 1}, {start_col + region_size - 1})\n"
                    f"区域大小: {region_size}×{region_size}\n"
                    f"图片大小: {img_width}×{img_height}")
            
            self.region_status_label.config(
                text=f"✓ {region_size}×{region_size} 从({start_row},{start_col})", 
                fg="green"
            )
            
            messagebox.showinfo("验证成功", info_msg)
            self.log(f"✓ 区域验证成功: {region_size}×{region_size} 从({start_row},{start_col})")
            
        except ValueError as e:
            error_msg = f"区域设置无效: {str(e)}"
            self.region_status_label.config(text="❌ 设置无效", fg="red")
            messagebox.showerror("验证失败", error_msg)
            self.log(f"✗ {error_msg}")

    def _get_region_info(self):
        """获取区域信息
        
        Returns:
            (start_row, start_col, size) 或 None
        """
        coord_str = self.region_coord_var.get()
        
        if not coord_str or not coord_str.strip():
            return None
        
        try:
            coords = self._parse_coordinates(coord_str)
            if coords is None:
                return None
            
            start_row, start_col = coords
            region_size = self.region_size_var.get()
            
            if region_size <= 0:
                raise ValueError("区域大小必须大于0")
            
            return (start_row, start_col, region_size)
        
        except ValueError as e:
            raise ValueError(f"坐标解析错误: {str(e)}")



    def parse_color_list(self, text):
        """解析颜色列表文本，支持多种格式"""
        import re
        import json
        
        text = text.strip()
        
        if not text:
            return []
        
        colors = []
        
        try:
            # 尝试作为JSON数组解析
            if text.startswith('[') and text.endswith(']'):
                colors = json.loads(text)
            # 尝试作为逗号分隔的字符串解析
            else:
                colors = [c.strip() for c in text.split(',')]
        except:
            # 如果JSON解析失败，尝试正则提取所有颜色代码
            # 匹配 #XXXXXX 或 XXXXXX 格式
            pattern = r'#?[0-9A-Fa-f]{6}'
            colors = re.findall(pattern, text)
        
        # 标准化颜色代码格式
        normalized_colors = []
        for color in colors:
            color = str(color).strip().upper()
            if not color:
                continue
            # 添加#号
            if not color.startswith('#'):
                color = '#' + color
            # 验证格式
            if len(color) == 7 and all(c in '0123456789ABCDEF' for c in color[1:]):
                normalized_colors.append(color)
        
        return normalized_colors
    
    def preview_color_list(self):
        """预览颜色列表信息（不实际点击）"""
        if not self.painter:
            messagebox.showerror("错误", "请先选择目标窗口")
            return
        
        # 获取输入文本
        text = self.color_test_text.get("1.0", "end-1c")
        
        try:
            # 解析颜色列表
            colors = self.parse_color_list(text)
            
            if not colors:
                messagebox.showerror("错误", "未找到有效的颜色代码")
                return
            
            # 获取每个颜色的信息
            preview_lines = [f"共找到 {len(colors)} 个颜色：\n"]
            
            for i, color in enumerate(colors, 1):
                try:
                    color_info = self.painter.color_mapper.get_color_position(color)
                    preview_lines.append(
                        f"{i}. {color} → 分类{color_info['category']}, 索引{color_info['index']}"
                    )
                except KeyError:
                    preview_lines.append(f"{i}. {color} → ❌ 不在调色板中")
            
            preview_lines.append(f"\n当前分类: {self.painter.current_category}")
            preview_lines.append("\n点击'确认并批量测试'执行实际选择操作")
            
            preview_msg = "\n".join(preview_lines)
            
            self.color_test_info.config(text=f"预览: 共{len(colors)}个颜色", fg="blue")
            self.log(f"预览颜色列表: {len(colors)}个颜色")
            
            messagebox.showinfo("颜色列表预览", preview_msg)
            
        except Exception as e:
            error_msg = f"解析颜色列表失败: {str(e)}"
            self.color_test_info.config(text=f"✗ {error_msg}", fg="red")
            messagebox.showerror("错误", error_msg)


    def confirm_batch_color_test(self):
        """确认并执行批量颜色选择测试"""
        if not self.painter:
            messagebox.showerror("错误", "请先选择目标窗口")
            return
        
        # 检查颜色选择器是否已校准
        if not self.painter.color_left_btn or not self.painter.color_right_btn:
            messagebox.showerror("错误", "请先校准颜色选择器（左右按钮）")
            return
        
        if not self.painter.color_positions:
            messagebox.showerror("错误", "请先标记颜色位置")
            return
        
        # 获取输入文本
        text = self.color_test_text.get("1.0", "end-1c")
        
        try:
            # 解析颜色列表
            colors = self.parse_color_list(text)
            
            if not colors:
                messagebox.showerror("错误", "未找到有效的颜色代码")
                return
            
            # 验证所有颜色是否存在
            invalid_colors = []
            valid_colors_info = []
            
            for color in colors:
                try:
                    color_info = self.painter.color_mapper.get_color_position(color)
                    valid_colors_info.append((color, color_info))
                except KeyError:
                    invalid_colors.append(color)
            
            # 如果有无效颜色，给出警告
            if invalid_colors:
                warning_msg = f"以下颜色不在调色板中，将被跳过：\n\n"
                warning_msg += "\n".join(invalid_colors)
                warning_msg += f"\n\n有效颜色数: {len(valid_colors_info)}/{len(colors)}\n\n是否继续测试有效颜色？"
                
                if not messagebox.askyesno("警告", warning_msg):
                    return
            
            # 弹出确认对话框
            confirm_lines = [
                f"即将执行批量颜色选择测试：\n",
                f"总颜色数: {len(colors)}",
                f"有效颜色数: {len(valid_colors_info)}",
                f"无效颜色数: {len(invalid_colors)}\n",
                f"测试列表："
            ]
            
            for i, (color, info) in enumerate(valid_colors_info[:10], 1):  # 只显示前10个
                confirm_lines.append(f"{i}. {color} → 分类{info['category']}, 索引{info['index']}")
            
            if len(valid_colors_info) > 10:
                confirm_lines.append(f"... 还有 {len(valid_colors_info) - 10} 个颜色")
            
            confirm_lines.append(f"\n当前分类: {self.painter.current_category}")
            confirm_lines.append("\n⚠️ 此操作将在游戏窗口中实际点击！")
            confirm_lines.append("确定要继续吗？")
            
            confirm_msg = "\n".join(confirm_lines)
            
            if not messagebox.askyesno("确认批量测试", confirm_msg):
                self.log("用户取消了批量颜色选择测试")
                return
            
            # 执行批量测试
            self.log(f"开始批量测试 {len(valid_colors_info)} 个颜色")
            
            success_count = 0
            fail_count = 0
            
            for i, (color, color_info) in enumerate(valid_colors_info, 1):
                try:
                    self.color_test_info.config(
                        text=f"正在测试 {i}/{len(valid_colors_info)}: {color}...", 
                        fg="orange"
                    )
                    self.root.update()
                    
                    # 更新窗口位置
                    self.painter.update_window_rect()
                    
                    # 选择颜色
                    self.painter.select_color(color)
                    
                    self.log(f"✓ [{i}/{len(valid_colors_info)}] {color} 测试成功 (分类{color_info['category']}, 索引{color_info['index']})")
                    success_count += 1
                    
                    # 每个颜色之间短暂延迟
                    time.sleep(0.3)
                    
                except Exception as e:
                    self.log(f"✗ [{i}/{len(valid_colors_info)}] {color} 测试失败: {str(e)}")
                    fail_count += 1
            
            # 显示完成信息
            result_msg = (f"批量测试完成！\n\n"
                        f"成功: {success_count}\n"
                        f"失败: {fail_count}\n"
                        f"跳过: {len(invalid_colors)}\n"
                        f"总计: {len(colors)}")
            
            self.color_test_info.config(
                text=f"✓ 完成: {success_count}成功, {fail_count}失败, {len(invalid_colors)}跳过", 
                fg="green" if fail_count == 0 else "orange"
            )
            
            messagebox.showinfo("测试完成", result_msg)
            
        except Exception as e:
            error_msg = f"✗ 批量测试失败: {str(e)}"
            self.color_test_info.config(text=error_msg, fg="red")
            self.log(error_msg)
            messagebox.showerror("错误", f"批量测试时出错:\n{str(e)}")
    
    # ============ 游戏窗口查找 ============
    def find_game_window(self):
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
    def test_coordinates(self):
        """测试坐标"""
        if not self.json_data:
            messagebox.showwarning("警告", "请先加载JSON文件")
            return
        
        if not self.painter.grid_start or not self.painter.grid_end:
            messagebox.showwarning("警告", "请先完成画板校准")
            return
        
        width = self.json_data['width']
        height = self.json_data['height']
        
        # 显示校准信息
        self.log("\n" + "="*60)
        self.log("🧪 开始坐标测试")
        self.log("="*60)
        self.log(f"画板校准: {self.painter.grid_start} -> {self.painter.grid_end}")
        self.log(f"图片尺寸: {width}x{height}")
        self.log(f"3秒后开始在5个位置点击...")
        self.log("="*60)
        
        def run_test():
            import time
            time.sleep(3)  # 3秒延迟，让用户准备
            
            try:
                self.painter.test_click_points(width, height)
                self.test_info.config(text="测试完成 ✓", fg="green")
                self.log("✓ 测试完成 - 检查画板上是否有5个点")
            except Exception as e:
                self.test_info.config(text="测试失败 ✗", fg="red")
                self.log(f"✗ 测试出错: {e}")
        
        threading.Thread(target=run_test, daemon=True).start()
        self.test_info.config(text="测试中...", fg="orange")
    def on_key_press(self, key):
        """键盘按键事件监听"""
        print(f"🎹 检测到按键: {key}")
        
        try:
            # P键 - 开始绘制
            if hasattr(key, 'char') and key.char and key.char.lower() == 'p':
                print("  → 识别为 P 键")
                if self.start_btn['state'] == 'normal':  # ✅ 只检查按钮状态
                    self.root.after(0, self.start_painting)
                    print("  → 触发开始绘制")
            
            # O键 - 暂停/恢复
            elif hasattr(key, 'char') and key.char and key.char.lower() == 'o':
                print(f"  → 识别为 O 键")
                if self.pause_btn['state'] == 'normal':  # ✅ 只检查按钮状态
                    self.root.after(0, self.pause_painting)
                    print("  → 触发暂停/恢复")
            
            # I键 - 停止
            elif hasattr(key, 'char') and key.char and key.char.lower() == 'i':
                print(f"  → 识别为 I 键")
                if self.stop_btn['state'] == 'normal':  # ✅ 只检查按钮状态
                    self.root.after(0, self.stop_painting)
                    print("  → 触发停止")
            
            # ESC键 - 紧急停止（无条件触发）
            elif key == keyboard.Key.esc:
                print("  → 识别为 ESC 键")
                self.root.after(0, self.emergency_stop)  # ✅ 直接调用
                print("  → 触发紧急停止")
            
            # J键 - 双击当前位置
            elif hasattr(key, 'char') and key.char and key.char.lower() == 'j':
                if self.is_tracking:
                    x, y = self.current_mouse_pos
                    self.root.after(0, lambda: win_input.double_click(x, y))
                    print(f"  → J键双击 ({x}, {y})")
            
            # Space键 - 确认坐标
            elif key == keyboard.Key.space and self.is_tracking:
                if self.calibration_mode:
                    x, y = self.current_mouse_pos
                    self.root.after(0, lambda: self._perform_confirmation_action(x, y, source="keyboard"))
                    print("  → Space键确认坐标")
            
            # 方向键
            elif self.is_tracking:
                from pynput.mouse import Controller
                mouse_controller = Controller()
                
                dx, dy = 0, 0
                if key == keyboard.Key.up:
                    dy = -self.cursor_step
                elif key == keyboard.Key.down:
                    dy = self.cursor_step
                elif key == keyboard.Key.left:
                    dx = -self.cursor_step
                elif key == keyboard.Key.right:
                    dx = self.cursor_step
                
                if dx != 0 or dy != 0:
                    new_x = self.current_mouse_pos[0] + dx
                    new_y = self.current_mouse_pos[1] + dy
                    mouse_controller.position = (new_x, new_y)
                    self.current_mouse_pos = (new_x, new_y)
                    self.root.after(0, lambda: self.coord_label.config(
                        text=f"当前坐标: X: {new_x}, Y: {new_y}"
                    ))
        
        except Exception as e:
            print(f"❌ on_key_press 异常: {e}")
            import traceback
            traceback.print_exc()

    def manual_click(self):
        """手动点击当前光标位置（双击）"""
        if not self.is_tracking:
            return
        
        x, y = self.current_mouse_pos
        win_input.double_click(x, y)  # 双击当前位置
        self.log(f"已在 ({x}, {y}) 执行双击")

    

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

    def select_target_window(self):
        """让用户选择目标窗口"""
        window_title = simpledialog.askstring(
            "选择窗口",
            "输入要控制的窗口标题(部分即可):\n例如: '心动小镇'\n\n"
            "或留空以自动使用当前前景窗口"
        )
        
        if window_title is not None:
            if window_title == "":
                hwnd = win32gui.GetForegroundWindow()
                window_title = win32gui.GetWindowText(hwnd)
            else:
                hwnd = win32gui.FindWindow(None, window_title)
                if not hwnd:
                    # 模糊查找
                    def callback(h, windows):
                        if win32gui.IsWindowVisible(h):
                            title = win32gui.GetWindowText(h)
                            if window_title.lower() in title.lower():
                                windows.append((h, title))
                    windows = []
                    win32gui.EnumWindows(callback, windows)
                    if windows:
                        hwnd = windows[0][0]
                        window_title = windows[0][1]
            
            if hwnd:
                print(hwnd)
                # 设置窗口
                from win_input import win_input
                self.painter.set_window(hwnd)
                win_input.lock_window(hwnd)
                
                self.window_label.config(
                    text=f"已锁定: {window_title[:30]}", 
                    fg="green"
                )
                self.log(f"✓ 已锁定窗口: {window_title}")
            else:
                self.log(f"❌ 未找到窗口: {window_title}")


    def toggle_tracking(self):
        """开始/停止追踪光标"""
        if not self.is_tracking:
            # 开始追踪
            self.is_tracking = True
            self.track_btn.config(text="停止校准", bg="#FF5722")
            self.cancel_button.config(state="normal")
            self.log("开始校准模式 - 使用方向键移动光标，按'J'键双击，按'Space'键确认坐标")
        else:
            # 停止追踪
            self.cancel_coordinates()


    
    def _save_confirmed_coordinate(self, x, y):
        """
        核心：将确认的 x, y 坐标保存到相应的校准属性中
        这个方法现在只负责保存逻辑，不负责获取坐标或重置UI状态
        """
        if self.calibration_mode == "grid_start":
            self.painter.grid_start = (x, y)
            self.log(f"✓ 画板左上角: ({x}, {y})")
            print([x,y])
            self.check_grid_calibration()
        
        elif self.calibration_mode == "grid_end":
            self.painter.grid_end = (x, y)
            self.log(f"✓ 画板右下角: ({x}, {y})")
            print([x,y])
            self.check_grid_calibration()
        
        elif self.calibration_mode == "color_left":
            self.painter.color_left_btn = (x, y)
            self.log(f"✓ 左切换按钮: ({x}, {y})")
            self.check_color_calibration()
        
        elif self.calibration_mode == "color_right":
            self.painter.color_right_btn = (x, y)
            self.log(f"✓ 右切换按钮: ({x}, {y})")
            self.check_color_calibration()
        
        elif self.calibration_mode.startswith("color_point_"):
            # 颜色点校准
            self.calibration_points.append((x, y))
            index = len(self.calibration_points)
            self.log(f"  颜色 {index}: ({x}, {y})")
        
        self.painter.save_config() # 每次保存后都更新配置
    
    def _perform_confirmation_action(self, x, y, source="keyboard"):
        """
        执行坐标确认的动作，无论是通过键盘还是按钮。
        它会调用 _save_confirmed_coordinate 来保存，并处理后续的UI状态重置。
        """
        if not self.is_tracking:
            self.log("未处于追踪模式，无法确认坐标。")
            return

        if self.calibration_mode:
            self._save_confirmed_coordinate(x, y) # 调用核心保存逻辑
            
            if source == "button":
                messagebox.showwarning("警告", "通过点击按钮确认坐标可能不准确。\n建议使用 'Space' 键在目标位置直接确认。")
            
            # 判断是否在批量标记颜色点
            if self.calibration_mode.startswith("color_point_"):
                # 颜色点标记：不重置状态，让 calibrate_color_point 递归继续
                self.coord_label.config(text=f"已确认坐标: X: {x}, Y: {y}")
                self.log(f"✓ 已确认颜色点 {len(self.calibration_points)}/{10}")
            else:
                # 单次校准：重置状态
                self.is_tracking = False
                self.track_btn.config(text="开始校准", bg="#2196F3")
                self.cancel_button.config(state="disabled")
                self.coord_label.config(text=f"已确认坐标: X: {x}, Y: {y}")
                self.calibration_mode = None
        else:
            self.log("未选择校准模式，无法确认坐标。")

    def cancel_coordinates(self):
        """取消坐标选择或重置追踪状态"""
        self.is_tracking = False
        self.track_btn.config(text="开始校准", bg="#2196F3")
        self.cancel_button.config(state="disabled")
        self.coord_label.config(text="当前坐标: X: 0, Y: 0")
        self.calibration_mode = None
        self.log("已取消校准模式")
    
    def start_calibration(self, mode):
        """开始坐标校准"""
        self.calibration_mode = mode
        mode_names = {
            "grid_start": "画板左上角",
            "grid_end": "画板右下角",
            "color_left": "左切换按钮",
            "color_right": "右切换按钮"
        }
        self.log(f"请使用方向键移动光标到 {mode_names.get(mode, mode)} 的位置，按'J'键测试双击，按'Space'键确认")
        
        # 自动开始追踪
        if not self.is_tracking:
            self.toggle_tracking()


    
    def calibrate_colors(self):
        """校准颜色位置(批量标记)"""
        result = messagebox.askquestion("颜色位置校准", 
                                        "需要标记10个颜色方块的位置\n"
                                        "请按从左到右、从上到下的顺序依次标记\n\n"
                                        "准备好了吗?")
        if result == 'yes':
            self.calibration_points = []
            self.calibrate_color_point(0, 10)
    
    def calibrate_color_point(self, index, total):
        """递归标记颜色点"""
        if index >= total:
            self.painter.color_positions = self.calibration_points
            self.painter.save_config()
            self.log(f"✓ 已标记 {total} 个颜色位置")
            self.check_color_calibration()
            
            # 完成所有标记后重置状态
            self.is_tracking = False
            self.track_btn.config(text="开始校准", bg="#2196F3")
            self.cancel_button.config(state="disabled")
            self.calibration_mode = None
            self.coord_label.config(text="颜色位置标记完成")
            return
        
        self.calibration_mode = f"color_point_{index}"
        self.log(f"请移动光标到第 {index + 1}/{total} 个颜色位置，然后按'Space'键确认坐标")
        
        # 自动开始追踪（仅第一次）
        if index == 0 and not self.is_tracking:
            self.toggle_tracking()
        
        # 等待用户通过键盘确认后再继续下一个
        def check_next():
            # 检查当前点是否已确认（通过判断 calibration_points 长度）
            if len(self.calibration_points) == index + 1:
                # 当前点已确认，继续下一个
                self.root.after(100, lambda: self.calibrate_color_point(index + 1, total))
            else:
                # 当前点未确认，继续等待
                self.root.after(100, check_next)
        
        self.root.after(100, check_next)

    def check_grid_calibration(self):
        """检查画板校准状态"""
        if self.painter.grid_start and self.painter.grid_end:
            self.grid_status.config(text="已校准 ✓", fg="green")
    
    def check_color_calibration(self):
        """检查颜色选择器校准状态"""
        if (self.painter.color_left_btn and 
            self.painter.color_right_btn and 
            len(self.painter.color_positions) >= 6): # 假设至少需要6个颜色点
            self.color_status.config(text="已校准 ✓", fg="green")
    
    def load_saved_config(self):
        """加载保存的配置"""
        if self.painter.config:
            if self.painter.config.get("grid_start"):
                self.painter.grid_start = tuple(self.painter.config["grid_start"])
            if self.painter.config.get("grid_end"):
                self.painter.grid_end = tuple(self.painter.config["grid_end"])
            if self.painter.config.get("color_left_btn"):
                self.painter.color_left_btn = tuple(self.painter.config["color_left_btn"])
            if self.painter.config.get("color_right_btn"):
                self.painter.color_right_btn = tuple(self.painter.config["color_right_btn"])
            if self.painter.config.get("color_positions"):
                self.painter.color_positions = [tuple(p) for p in self.painter.config["color_positions"]]
            
            self.check_grid_calibration()
            self.check_color_calibration()
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
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    self.json_data = json.load(f)
                
                width = self.json_data["width"]
                height = self.json_data["height"]
                
                # 计算总颜色数
                pixels = self.json_data["pixels"]
                unique_colors = set()
                for row in pixels:
                    for color in row:
                        unique_colors.add(color.upper())
                
                total_colors = len(unique_colors)
                
                self.file_label.config(
                    text=f"已加载: {os.path.basename(filename)} ({width}x{height})",
                    fg="green"
                )
                
                # ✅ 直接使用保存的引用
                self.total_colors_label.config(text=f"总颜色数: {total_colors}")
                self.start_color_spinbox.config(to=total_colors)
                
                self.log(f"加载文件成功: {width}x{height}, 总颜色数: {total_colors}")
                
            except Exception as e:
                messagebox.showerror("错误", f"加载文件失败:\n{str(e)}")
                self.log(f"加载文件失败: {str(e)}")

    def start_painting(self):
        """开始绘制"""
        if not self.painter:
            messagebox.showerror("错误", "请先选择目标窗口")
            return
        
        if not self.json_data:
            messagebox.showerror("错误", "请先加载JSON文件")
            return
        
        if not self.painter.grid_start or not self.painter.grid_end:
            messagebox.showerror("错误", "请先完成画板校准")
            return
        
        if not self.painter.color_positions:
            messagebox.showerror("错误", "请先标记颜色位置")
            return
        
        # 获取区域信息
        try:
            region_info = self._get_region_info()
        except ValueError as e:
            messagebox.showerror("错误", f"区域设置错误:\n{str(e)}")
            return
        
        # 获取起始颜色索引
        start_color_index = self.start_color_index.get()
        
        # 构建确认消息
        confirm_msg = ""
        
        if region_info:
            start_row, start_col, region_size = region_info
            confirm_msg = (f"区域绘制设置：\n\n"
                        f"起始坐标: [{start_row}, {start_col}]\n"
                        f"区域大小: {region_size}×{region_size}\n"
                        f"结束坐标: [{start_row + region_size - 1}, {start_col + region_size - 1}]\n\n")
        else:
            confirm_msg = "将绘制整张图片\n\n"
        
        if start_color_index > 1:
            confirm_msg += f"起始颜色: 第 {start_color_index} 个\n"
        
        confirm_msg += "\n确定要开始绘制吗？"
        
        if not messagebox.askyesno("确认开始", confirm_msg):
            return
        
        # ✅ 关键：设置绘制标志（在禁用按钮之前）
        self.is_painting = True
        print(f"✅ 设置 is_painting = True")
        
        # 禁用开始按钮，启用暂停和停止按钮
        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="normal")
        self.stop_btn.config(state="normal")
        
        # 记录日志
        if region_info:
            start_row, start_col, region_size = region_info
            self.log(f"开始区域绘制: [{start_row}, {start_col}] 大小 {region_size}×{region_size}, 起始颜色索引: {start_color_index}")
        else:
            self.log(f"开始全图绘制，起始颜色索引: {start_color_index}")
        
        # 在新线程中执行绘制
        self.paint_thread = threading.Thread(
            target=self._paint_worker,
            args=(start_color_index, region_info),
            daemon=True
        )
        self.paint_thread.start()

    def _paint_worker(self, start_color_index=1, region_info=None):
        """绘制工作线程
        
        Args:
            start_color_index: 起始颜色索引
            region_info: (start_row, start_col, size) 或 None
        """
        try:
            self.painter.paint_from_json(
                self.json_data, 
                progress_callback=self.update_progress,
                start_color_index=start_color_index,
                region_info=region_info  # ✅ 传递区域信息
            )
            
            self.root.after(0, lambda: messagebox.showinfo("完成", "绘制完成1！"))
            self.root.after(0, self.log, "绘制完成2")
            
        except Exception as e:
            error_msg = f"绘制过程出错: {str(e)}"
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
            self.root.after(0, self.log, error_msg)
        
        finally:
            # 恢复按钮状态
            self.root.after(0, self.start_btn.config, {"state": "normal"})
            self.root.after(0, self.pause_btn.config, {"state": "disabled"})
            self.root.after(0, self.stop_btn.config, {"state": "disabled"})

    def update_progress(self, current, total, color, color_index=None, total_colors=None, category=None):
        print(f"DEBUG: update_progress called with {len(locals())} parameters") 
        """更新进度 - 必须在主线程中执行
        
        Args:
            current: 当前像素数
            total: 总像素数
            color: 当前颜色代码
            color_index: 当前颜色索引（可选）
            total_colors: 总颜色数（可选）
            category: 颜色分类（可选）
        """
        def _update():
            progress = (current / total) * 100 if total > 0 else 0
            self.progress_bar['value'] = progress
            
            # 主进度信息
            progress_text = f"进度: {current}/{total} ({progress:.1f}%)"
            
            # 颜色分组信息
            if color_index is not None and total_colors is not None:
                progress_text += f" | 颜色: {color_index}/{total_colors}"
            
            self.progress_label.config(text=progress_text)
            
            # 详细信息
            detail_text = f"当前颜色: {color}"
            if category is not None:
                detail_text += f" (分类 {category})"
            
            self.detail_label.config(text=detail_text)
        
        # 确保在主线程中更新UI
        self.root.after(0, _update)

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
    
    # def update_progress(self, current, total, color):
    #     """更新进度"""
    #     progress = (current / total) * 100
    #     self.progress_bar['value'] = progress
    #     self.progress_label.config(
    #         text=f"进度: {current}/{total} ({progress:.1f}%) | 当前颜色: {color}"
    #     )
    
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

