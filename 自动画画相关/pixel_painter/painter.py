import json
import time
import os
import win32gui
from color_mapper import ColorMapper
from win_input import win_input
import math

class PixelPainter:
    def __init__(self):
        self.color_mapper = ColorMapper()
        
        # 窗口信息
        self.window_hwnd = None
        self.window_rect = None
        
        # 画板相对于窗口的位置
        self.canvas_offset_x = 0  # 画板中心相对窗口中心的X偏移
        self.canvas_offset_y = 0  # 画板中心相对窗口中心的Y偏移
        self.canvas_width = 582   # 画板宽度
        self.canvas_height = 582  # 画板高度
        
        # 旧的绝对坐标（用于GUI显示）
        self.grid_start = None
        self.grid_end = None
        
        # 颜色选择器坐标
        self.color_left_btn = None
        self.color_right_btn = None
        self.color_positions = []
        
        # 状态控制
        self.is_paused = False
        self.is_stopped = False
        self.current_category = 1
        
        # 配置文件
        self.config_file = "painter_config.json"
        self.config = self.load_config()
    
    def set_window(self, hwnd):
        """设置目标窗口"""
        self.window_hwnd = hwnd
        self.update_window_rect()
        # self.log_window_info()
    
    def update_window_rect(self):
        """更新窗口位置（窗口可能移动）"""
        if self.window_hwnd:
            self.window_rect = win32gui.GetWindowRect(self.window_hwnd)
            print('窗口位置：',self.window_rect)
            return True
        return False

    def calculate_pixel_pos(self, row, col, width, height):
        """计算像素格的中心坐标"""
        if not self.grid_start or not self.grid_end:
            raise Exception("画板未校准")
        
        # left, top = self.grid_start
        # right, bottom = self.grid_end

        SCALE_FACTOR = 1.5
        win32_left, win32_top = [544,277]
        win32_right, win32_bottom = [1129,862]

        # win32_left, win32_top = [round(left/SCALE_FACTOR),round(top/SCALE_FACTOR)]
        # win32_right, win32_bottom = [round(right/SCALE_FACTOR),round(bottom/SCALE_FACTOR)]
        
        # 画板在 pynput 坐标系中的尺寸
        canvas_width = win32_right - win32_left
        canvas_height = win32_bottom - win32_top
        
        # 每个像素格的尺寸
        pixel_width = canvas_width / width
        pixel_height = canvas_height / height
        
        # 计算中心坐标（pynput 坐标系）
        win32_x = math.floor(win32_left + col * pixel_width)
        win32_y = math.floor(win32_top + row * pixel_height)
        
        print(f"像素({row},{col}): win32({win32_x},{win32_y})")
        
        return (win32_x, win32_y)

    
    def test_click_points(self, width, height):
        """测试绘制 - 在中心和四个角各画一个点"""
        self.update_window_rect()

        print("\n" + "="*10)
        print("🧪 坐标测试模式 - 将在5个位置各点击一次")
        print("="*10)

        
        # 在这确认偏移量应用
        test_points = [
            (height // 2, width // 2, "中心"),
            (0, 0, "左上角"),
            (0, width - 1, "右上角"),
            (height - 1, 0, "左下角"),
            (height - 1, width - 1, "右下角"),
        ]
        
        for row, col, position_name in test_points:
            # 计算位置
            x, y = self.calculate_pixel_pos(row, col, width, height)

            print(f"\n📍 {position_name}")
            print(f"   像素坐标: ({row}, {col})")
            print(f"   屏幕坐标: ({x}, {y})")

            # 点击测试点
            win_input.click(x, y)
            time.sleep(0.3)

        # # 固定参数
        # canvas_center = (835, 568)
        # offset = 291  # 半边长 291

        # # 计算画板的五个坐标点
        # test_points = [
        #     (canvas_center[1], canvas_center[0], "中心"),  # 画板中心
        #     (canvas_center[1] - offset, canvas_center[0] - offset, "左上角"),  # 左上角
        #     (canvas_center[1] - offset, canvas_center[0] + offset, "右上角"),  # 右上角
        #     (canvas_center[1] + offset, canvas_center[0] - offset, "左下角"),  # 左下角
        #     (canvas_center[1] + offset, canvas_center[0] + offset, "右下角"),  # 右下角
        # ]

        # for y, x, position_name in test_points:
        #     print(f"\n📍 {position_name}")
        #     print(f"   像素坐标: ({y}, {x})")
        #     print(f"   屏幕坐标: ({x}, {y})")

        #     # 执行点击
        #     win_input.click(x, y)
        #     time.sleep(0.3)

        print("\n" + "="*60)
        print("✓ 测试完成")
        print("="*60 + "\n")

    def save_config(self):
        """保存配置"""
        config = {
            "window_hwnd": self.window_hwnd,
            "canvas_offset_x": 0,
            "canvas_offset_y": 0,
            "canvas_width": self.canvas_width,
            "canvas_height": self.canvas_height,
            "grid_start": self.grid_start,
            "grid_end": self.grid_end,
            "color_left_btn": self.color_left_btn,
            "color_right_btn": self.color_right_btn,
            "color_positions": self.color_positions
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def load_config(self):
        """加载配置 - 使用绝对坐标"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 直接加载绝对坐标
                self.grid_start = tuple(config["grid_start"]) if config.get("grid_start") else None
                self.grid_end = tuple(config["grid_end"]) if config.get("grid_end") else None
                self.color_left_btn = tuple(config["color_left_btn"]) if config.get("color_left_btn") else None
                self.color_right_btn = tuple(config["color_right_btn"]) if config.get("color_right_btn") else None
                self.color_positions = [tuple(p) for p in config.get("color_positions", [])]
                
                print("✓ 已加载保存的坐标配置（绝对屏幕坐标）")
                return config
                
            except Exception as e:
                print(f"加载配置失败: {e}")
                return {}
        return {}

    def save_config(self):
        """保存配置 - 使用绝对坐标"""
        config = {
            "grid_start": list(self.grid_start) if self.grid_start else None,
            "grid_end": list(self.grid_end) if self.grid_end else None,
            "color_left_btn": list(self.color_left_btn) if self.color_left_btn else None,
            "color_right_btn": list(self.color_right_btn) if self.color_right_btn else None,
            "color_positions": [list(p) for p in self.color_positions]
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print("✓ 配置已保存")

    def switch_to_category(self, target_category):
        """切换到指定颜色分类"""
        if target_category == self.current_category:
            return
        
        # 计算需要点击的次数和方向
        diff = target_category - self.current_category
        
        if diff > 0:
            # 向右切换
            button = self.color_right_btn
            clicks = diff
            print('向右切换')

        else:
            # 向左切换
            button = self.color_left_btn
            clicks = abs(diff)
            print('向左切换')
        
        # 执行切换
        for _ in range(clicks):
            win_input.click(1200,900)
            win_input.click(button[0], button[1])
            time.sleep(0.5)  # 等待切换动画
        
        self.current_category = target_category
    
    def select_color(self, hex_color):
        """选择指定颜色"""
        # 获取颜色在调色板中的位置
        position = self.color_mapper.get_color_position(hex_color)
        category = position["category"]
        index = position["index"]
        
        # 切换到对应分类
        self.switch_to_category(category)
        
        # 点击对应的颜色块
        if index < len(self.color_positions):
            color_pos = self.color_positions[index]
            win_input.click(color_pos[0], color_pos[1])
            time.sleep(0.02)
        else:
            raise Exception(f"颜色索引 {index} 超出范围")
        
    
    def paint_from_json(self, json_data, progress_callback=None, start_color_index=1, region_info=None):
        """从JSON数据绘制像素画
        
        Args:
            json_data: 像素数据
            progress_callback: 进度回调函数
            start_color_index: 从第几个颜色开始绘制
            region_info: (start_row, start_col, size) 区域信息，None表示绘制全图
        """
        width = json_data["width"]
        height = json_data["height"]
        pixels = json_data["pixels"]
        
        # 定义要跳过的背景色
        BACKGROUND_COLORS = {"#F9F6E9"}
        
        self.is_stopped = False
        self.is_paused = False
        
        print(f"\n{'='*50}")
        print(f"原始图片大小: {width}×{height}")
        
        # ✅ 处理区域信息
        if region_info:
            start_row, start_col, region_size = region_info
            
            print(f"区域绘制模式启用")
            print(f"起始坐标: [{start_row}, {start_col}]")
            print(f"区域大小: {region_size}×{region_size}")
            
            # ✅ 验证区域边界
            end_row = min(start_row + region_size, height)
            end_col = min(start_col + region_size, width)
            
            actual_height = end_row - start_row
            actual_width = end_col - start_col
            
            print(f"实际绘制区域: {actual_width}×{actual_height}")
            
            if actual_height <= 0 or actual_width <= 0:
                print(f"❌ 区域无效，无像素可绘制")
                return
            
            # ✅ 裁剪像素数据
            cropped_pixels = []
            for row in range(start_row, end_row):
                if row < len(pixels):
                    row_data = pixels[row]
                    if start_col < len(row_data):
                        cropped_pixels.append(row_data[start_col:end_col])
            
            if not cropped_pixels:
                print(f"❌ 裁剪后无像素数据")
                return
            
            # 更新参数
            pixels = cropped_pixels
            width = actual_width
            height = len(cropped_pixels)
            
            print(f"裁剪后像素数据: {width}×{height}, 共 {len(cropped_pixels)} 行")
        else:
            print(f"全图绘制模式")
        
        print(f"背景色（将跳过）: {', '.join(BACKGROUND_COLORS)}")
        print(f"{'='*50}\n")
        
        total_pixels = width * height
        current_pixel = 0
        
        if total_pixels == 0:
            print("❌ 没有像素需要绘制")
            return
        
        print(f"开始处理，总像素数: {total_pixels}")
        
        try:
            # 按颜色分组绘制
            color_groups = self._group_pixels_by_color(pixels, width, height)
            
            print(f"初始颜色分组数: {len(color_groups)}")
            
            # 过滤背景色
            original_count = len(color_groups)
            color_groups = {color: positions for color, positions in color_groups.items() 
                        if color.upper() not in BACKGROUND_COLORS}
            
            skipped_bg_count = original_count - len(color_groups)
            if skipped_bg_count > 0:
                print(f"✓ 已过滤 {skipped_bg_count} 个背景色分组")
            
            total_color_count = len(color_groups)
            print(f"有效颜色分组数: {total_color_count}")
            
            if total_color_count == 0:
                print("❌ 过滤后没有有效颜色需要绘制")
                return
            
            # 转换为列表以支持索引
            color_items = list(color_groups.items())
            
            # 验证起始索引
            if start_color_index < 1:
                start_color_index = 1
            if start_color_index > total_color_count:
                print(f"⚠️ 起始颜色索引 {start_color_index} 超过总颜色数 {total_color_count}，从第一个开始")
                start_color_index = 1
            
            print(f"从第 {start_color_index} 个颜色开始绘制")
            print(f"{'='*50}\n")
            
            # 计算跳过的像素数
            skipped_pixels = 0
            if start_color_index > 1:
                for i in range(start_color_index - 1):
                    skipped_pixels += len(color_items[i][1])
                current_pixel = skipped_pixels
                print(f"已跳过前 {start_color_index - 1} 个颜色，共 {skipped_pixels} 个像素\n")
            
            # 从指定颜色开始绘制
            for color_index in range(start_color_index - 1, total_color_count):
                if self.is_stopped:
                    print("用户停止绘制")
                    break
                
                color, positions = color_items[color_index]
                
                print(f"[{color_index + 1}/{total_color_count}] 处理颜色: {color}, 像素数: {len(positions)}")
                
                # 选择当前颜色
                try:
                    if self.is_stopped:
                        break
                    
                    self.select_color(color)
                    print(f"  ✓ 已选择颜色")
                    
                    # 获取颜色分类信息
                    color_info = self.color_mapper.get_color_position(color)
                    current_category = color_info['category']
                    
                except Exception as e:
                    print(f"  ✗ 颜色选择失败: {e}")
                    current_pixel += len(positions)
                    if progress_callback:
                        progress_callback(current_pixel, total_pixels, color, 
                                        color_index + 1, total_color_count, None)
                    continue
                
                # 绘制该颜色的所有像素
                painted_count = 0
                for pixel_index, (row, col) in enumerate(positions):
                    # 检查暂停状态
                    while self.is_paused and not self.is_stopped:
                        time.sleep(0.01)
                    
                    if self.is_stopped:
                        print(f"  ! 在像素 {pixel_index}/{len(positions)} 处停止")
                        break
                    
                    try:
                        # ✅ 如果是区域绘制，需要加上偏移量
                        actual_row = row
                        actual_col = col
                        if region_info:
                            actual_row = start_row + row
                            actual_col = start_col + col
                        
                        x, y = self.calculate_pixel_pos(actual_row, actual_col, 
                                                    json_data["width"], json_data["height"])
                        win_input.click(x, y)
                        painted_count += 1
                        
                        if self.is_stopped:
                            break
                        if pixel_index % 20 == 0:
                            time.sleep(0.001)  # 减少到1ms
                        
                    except Exception as e:
                        print(f"  ! 绘制像素 ({row}, {col}) 失败: {e}")
                    
                    # 更新进度
                    current_pixel += 1
                    if progress_callback and pixel_index % max(1, len(positions) // 10) == 0:
                        progress_callback(current_pixel, total_pixels, color, 
                                        color_index + 1, total_color_count, current_category)
                
                print(f"  ✓ 完成 {painted_count}/{len(positions)} 个像素")
                
                if self.is_stopped:
                    break
                
                # 每组完成后更新进度
                if progress_callback:
                    progress_callback(current_pixel, total_pixels, color, 
                                    color_index + 1, total_color_count, current_category)
            
            print(f"\n{'='*50}")
            if self.is_stopped:
                print(f"绘制已停止，已完成 {current_pixel}/{total_pixels} 像素")
            else:
                print(f"✓ 绘制流程完成，总像素数: {current_pixel}/{total_pixels}")
            print(f"{'='*50}\n")
        
        except Exception as e:
            import traceback
            print(f"\n绘制异常: {e}")
            print(traceback.format_exc())
            raise

    def _group_pixels_by_color(self, pixels, width, height):
        """将像素按颜色分组"""
        color_groups = {}
        
        for row in range(height):
            for col in range(width):
                color = pixels[row][col].upper()
                
                if color not in color_groups:
                    color_groups[color] = []
                
                color_groups[color].append((row, col))
        
        return color_groups
    
    def pause(self):
        """暂停绘制"""
        self.is_paused = True
    
    def resume(self):
        """恢复绘制"""
        self.is_paused = False
    
    def stop(self):
        """停止绘制"""
        self.is_stopped = True
        self.is_paused = False
