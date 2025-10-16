"""
Windows输入控制模块 - 处理鼠标和键盘操作
"""
import win32gui
import win32api
import win32con
import time
import ctypes

class WindowsInput:
    def __init__(self):
        self.target_hwnd = None
        self.locked_hwnd = None # 添加锁定窗口
    
    def lock_window(self, hwnd):
        """锁定目标窗口"""
        self.locked_hwnd = hwnd
        self.target_hwnd = hwnd
        print(f"窗口已锁定: {hwnd}")
    
    def unlock_window(self):
        """解锁窗口"""
        self.locked_hwnd = None
        print("窗口已解锁")
    
    def focus_window(self):
        """将目标窗口置为前景窗口"""
        hwnd = self.locked_hwnd if self.locked_hwnd else self.target_hwnd
        if hwnd:
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.05)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.05)
            except:
                pass
    def click(self, x, y):
        """在指定坐标点击"""
        try:
            # 确保目标窗口有焦点
            self.focus_window()
            # time.sleep(0.05)
            
            # 移动鼠标
            win32api.SetCursorPos((x, y))
            time.sleep(0.01)
            
            # 点击
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.02)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.02)
        except Exception as e:
            print(f"点击失败: {e}")

    def double_click(self, x, y):
        """在指定坐标双击"""
        try:
            # 确保目标窗口有焦点
            self.focus_window()
            
            # 移动鼠标
            win32api.SetCursorPos((x, y))
            time.sleep(0.01)
            
            # 第一次点击
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.02)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.05)  # 两次点击之间的间隔
            
            # 第二次点击
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.02)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.02)
        except Exception as e:
            print(f"双击失败: {e}")
    
    def move_mouse(self, x, y):
        """移动鼠标到指定位置"""
        win32api.SetCursorPos((x, y))

# 全局实例
win_input = WindowsInput()
