"""
主程序入口
"""
import tkinter as tk
from gui import PixelPainterGUI
import ctypes
import sys
import traceback
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('painter_error.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def is_admin():
    """检查是否有管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception as e:
        logging.error(f"检查管理员权限失败: {e}")
        return False

def run_as_admin():
    """请求管理员权限并重新运行"""
    try:
        if not is_admin():
            logging.info("正在请求管理员权限...")
            ctypes.windll.shell32.ShellExecuteW(
                None, 
                "runas", 
                sys.executable, 
                " ".join([f'"{arg}"' for arg in sys.argv]), 
                None, 
                1
            )
            sys.exit()
    except Exception as e:
        logging.error(f"请求管理员权限失败: {e}")
        print(f"警告: 无法获取管理员权限，某些功能可能受限")
        print(f"错误: {e}")

def test_imports():
    """测试所有必要模块的导入"""
    modules = {
        'gui': None,
        'painter': None,
        'color_mapper': None,
        'win_input': None
    }
    
    all_success = True
    
    for module_name in modules.keys():
        try:
            if module_name == 'gui':
                from gui import PixelPainterGUI
                modules[module_name] = PixelPainterGUI
            elif module_name == 'painter':
                from painter import PixelPainter
                modules[module_name] = PixelPainter
            elif module_name == 'color_mapper':
                from color_mapper import ColorMapper
                modules[module_name] = ColorMapper
            elif module_name == 'win_input':
                from win_input import win_input
                modules[module_name] = win_input
            
            logging.info(f"✓ {module_name}.py 导入成功")
            
        except ImportError as e:
            logging.error(f"✗ {module_name}.py 导入失败: {e}")
            print(f"❌ 缺少模块: {module_name}.py")
            all_success = False
        except Exception as e:
            logging.error(f"✗ {module_name}.py 加载错误: {e}")
            traceback.print_exc()
            all_success = False
    
    return all_success

def main():
    """主函数"""
    print("="*60)
    print("像素画自动填充工具 - 启动中...")
    print("="*60)
    
    try:
        # 1. 请求管理员权限
        logging.info("检查管理员权限...")
        run_as_admin()
        
        # 2. 测试模块导入
        logging.info("检查必要模块...")
        if not test_imports():
            raise ImportError("部分模块导入失败，请检查所有 .py 文件是否存在")
        
        # 3. 创建GUI
        logging.info("正在启动GUI界面...")
        root = tk.Tk()
        app = PixelPainterGUI(root)
        
        logging.info("✓ 程序启动成功!")
        print("\n✅ 程序已启动，窗口已打开")
        print("="*60 + "\n")
        
        # 4. 运行主循环
        root.mainloop()
        
        logging.info("程序正常退出")
    
    except ImportError as e:
        logging.critical(f"导入错误: {e}", exc_info=True)
        print("\n" + "="*60)
        print("❌ 导入错误")
        print("="*60)
        print(f"错误: {e}")
        print("\n请确保以下文件存在于同一目录:")
        print("  - gui.py")
        print("  - painter.py")
        print("  - color_mapper.py")
        print("  - win_input.py")
        print("="*60)
        input("\n按 Enter 键退出...")
        sys.exit(1)
    
    except tk.TclError as e:
        logging.critical(f"Tkinter错误: {e}", exc_info=True)
        print("\n" + "="*60)
        print("❌ GUI界面错误")
        print("="*60)
        print(f"错误: {e}")
        print("\n可能的原因:")
        print("  1. 显示器配置问题")
        print("  2. Tkinter库损坏")
        print("  3. 系统缺少必要的图形库")
        print("="*60)
        input("\n按 Enter 键退出...")
        sys.exit(1)
    
    except Exception as e:
        # 捕获所有其他异常
        logging.critical(f"未知错误: {e}", exc_info=True)
        print("\n" + "="*60)
        print("❌ 程序崩溃")
        print("="*60)
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        print("\n完整堆栈跟踪:")
        print("-"*60)
        traceback.print_exc()
        print("-"*60)
        print(f"\n详细日志已保存到: painter_error.log")
        print("="*60)
        input("\n按 Enter 键退出...")
        sys.exit(1)
    
    finally:
        logging.info(f"程序结束于: {datetime.now()}")

if __name__ == "__main__":
    main()
