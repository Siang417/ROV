import sys
import Scrcpy_stream as scrcpy
import Get_ROI as ROI
import Image_Process as IP
import cv2 as cv
import numpy as np
import time
import threading
import pygetwindow as gw
import Image_OCR as OCR
import BrockenNet_record as BD
import keyboard
import atexit
import signal

# 全局變量來追蹤資源
scrcpy_process = None
threads_list = []

def main():
    """主程式入口點"""
    global scrcpy_process, threads_list
    
    print("啟動破網檢測系統...")
    
    # 設置程式退出時的清理函數
    atexit.register(cleanup_on_exit)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 啟用偵錯模式
    ROI.roi.debug_mode = True
    IP.ImageProcessor.debug_mode = True
    OCR.ImageOCR.debug_mode = True
    BD.BreaknetDetection.debug_mode = True
    
    # 設置 ROI 模組的 image_processor 引用
    ROI.roi.image_processor = IP.ImageProcessor

    # 啟動 ADB 伺服器
    scrcpy.stream.start_adb_server()
    
    # 檢查設備連接
    device_id = scrcpy.stream.check_devices()
    if not device_id:
        print("未找到設備，程式結束")
        return
    
    # 啟動 scrcpy
    try:
        cmd = [
            "scrcpy",
            "-s", device_id,
            "--window-title", f"scrcpy-{device_id}"
        ]
        import subprocess
        scrcpy_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("已啟動 scrcpy 視窗")
    except Exception as e:
        print(f"啟動 scrcpy 時發生錯誤: {e}")
        return
    
    # 等待 scrcpy 視窗出現
    print("等待 scrcpy 視窗啟動...")
    time.sleep(3)
    
    # 尋找 scrcpy 視窗
    found_window = False
    for _ in range(5):
        ROI.roi.find_scrcpy_window()
        if ROI.roi.scrcpy_window is not None:
            found_window = True
            break
        time.sleep(1)
    
    if not found_window:
        print("無法找到 scrcpy 視窗，請確保 scrcpy 已正確啟動")
        cleanup_resources()
        return
    
    # 初始化破網檢測模組
    print("正在初始化破網檢測模組...")
    try:
        BD.BreaknetDetection.running = True
        if BD.BreaknetDetection.initialize():
            print("破網檢測模組初始化成功")
        else:
            print("破網檢測模組初始化失敗")
            cleanup_resources()
            return
    except Exception as e:
        print(f"破網檢測模組初始化失敗: {e}")
        cleanup_resources()
        return
    
    # 啟動影像處理線程
    try:
        image_processing_thread = IP.ImageProcessor.start_processing(ROI)
        if image_processing_thread:
            threads_list.append(image_processing_thread)
    except Exception as e:
        print(f"啟動影像處理線程失敗: {e}")

    # 啟動 OCR 處理模組
    try:
        ocr_thread = OCR.ImageOCR.start_ocr(IP.ImageProcessor)
        if ocr_thread:
            threads_list.append(ocr_thread)
    except Exception as e:
        print(f"啟動 OCR 處理模組失敗: {e}")
    
    # 設置全局熱鍵
    setup_global_hotkeys()
    
    # 顯示操作說明
    print_instructions()

    try:
        # 啟動鍵盤監聽（這會阻塞直到按 'q'）
        ROI.roi.keyboard_worker()
    except KeyboardInterrupt:
        print("\n接收到中斷信號，正在退出...")
    except Exception as e:
        print(f"鍵盤監聽發生錯誤: {e}")
    finally:
        # 清理資源
        cleanup_resources()

def print_instructions():
    """顯示操作說明"""
    print("\n請使用以下按鍵操作:")
    print("基本功能:")
    print("- 按 's' 鍵進入選擇模式")
    print("- 按 'r' 鍵重置選擇區域")
    print("- 按 'd' 鍵切換處理方法")
    print("- 按 'p' 鍵保存處理後的圖像")
    print("- 按 'q' 鍵退出程式")
    print("- 按 'o' 鍵切換 OCR 結果視窗")
    print("- 按 't' 鍵切換 OCR 調試模式")
    print("\n破網檢測功能:")
    print("- 按 '1'-'5' 選擇檢測面")
    print("- 按 'b' 記錄當前水深")
    print("- 按 'v' 查看最近記錄")
    print("- 按 'c' 顯示當前狀態")
    print("- 按 'x' 匯出統計摘要")

def setup_global_hotkeys():
    """設置破網檢測相關的全局熱鍵"""
    try:
        # 基本功能按鍵
        keyboard.on_press_key('p', lambda _: safe_call(IP.ImageProcessor, 'save_processed_image'))
        keyboard.on_press_key('d', lambda _: safe_call(IP.ImageProcessor, 'display_intermediate_results'))
        keyboard.add_hotkey('o', lambda: safe_call(OCR.ImageOCR, 'toggle_result_window'))
        keyboard.add_hotkey('t', lambda: safe_call(OCR.ImageOCR, 'toggle_debug_mode'))
        
        # 破網檢測功能按鍵
        keyboard.add_hotkey('1', lambda: safe_call(BD.BreaknetDetection, 'set_detection_surface', 1))
        keyboard.add_hotkey('2', lambda: safe_call(BD.BreaknetDetection, 'set_detection_surface', 2))
        keyboard.add_hotkey('3', lambda: safe_call(BD.BreaknetDetection, 'set_detection_surface', 3))
        keyboard.add_hotkey('4', lambda: safe_call(BD.BreaknetDetection, 'set_detection_surface', 4))
        keyboard.add_hotkey('5', lambda: safe_call(BD.BreaknetDetection, 'set_detection_surface', 5))
        keyboard.add_hotkey('b', lambda: record_current_depth())
        keyboard.add_hotkey('v', lambda: safe_call(BD.BreaknetDetection, 'show_recent_records'))
        keyboard.add_hotkey('c', lambda: safe_call(BD.BreaknetDetection, 'display_current_status'))
        keyboard.add_hotkey('x', lambda: safe_call(BD.BreaknetDetection, 'export_daily_summary'))
        
        print("破網檢測熱鍵設置完成")
    except Exception as e:
        print(f"設置熱鍵時發生錯誤: {e}")

def safe_call(module, method_name, *args):
    """安全調用方法，如果方法不存在則跳過"""
    try:
        if hasattr(module, method_name):
            method = getattr(module, method_name)
            if callable(method):
                if args:
                    result = method(*args)
                else:
                    result = method()
                print(f"已調用 {module.__name__}.{method_name}")
                return result
            else:
                print(f"{module.__name__}.{method_name} 不是可調用的方法")
        else:
            print(f"{module.__name__} 沒有 {method_name} 方法")
    except Exception as e:
        print(f"調用 {module.__name__}.{method_name} 時發生錯誤: {e}")

def record_current_depth():
    """記錄當前 OCR 識別的水深"""
    try:
        # 嘗試獲取當前 OCR 結果
        current_ocr_result = None
        
        if hasattr(OCR.ImageOCR, 'last_result'):
            current_ocr_result = OCR.ImageOCR.last_result
        elif hasattr(OCR.ImageOCR, 'get_last_result'):
            current_ocr_result = OCR.ImageOCR.get_last_result()
        else:
            current_ocr_result = "無法獲取 OCR 結果"
            
        # 記錄到破網檢測模組
        if hasattr(BD.BreaknetDetection, 'record_depth_measurement'):
            success = BD.BreaknetDetection.record_depth_measurement(current_ocr_result)
            if success:
                print(f"已記錄水深: {current_ocr_result}")
            else:
                print(f"記錄水深失敗")
        else:
            print("破網檢測模組沒有 record_depth_measurement 方法")
            
    except Exception as e:
        print(f"記錄水深時發生錯誤: {e}")

def signal_handler(signum, frame):
    """處理系統信號"""
    print(f"\n接收到信號 {signum}，正在退出...")
    cleanup_resources()
    sys.exit(0)

def cleanup_on_exit():
    """程式退出時的清理函數"""
    cleanup_resources()

def cleanup_resources():
    """清理所有資源"""
    global scrcpy_process, threads_list
    
    print("正在清理資源...")
    
    try:
        # 停止所有模組的運行標誌
        ROI.roi.running = False
        IP.ImageProcessor.running = False
        OCR.ImageOCR.running = False
        BD.BreaknetDetection.running = False
        
        # 等待線程結束
        for thread in threads_list:
            if thread and thread.is_alive():
                print(f"等待線程 {thread.name} 結束...")
                thread.join(timeout=2)  # 最多等待2秒
        
        # 停止圖像處理
        try:
            IP.ImageProcessor.stop_processing()
        except Exception as e:
            print(f"停止圖像處理時發生錯誤: {e}")
        
        # 清理各模組
        safe_call(ROI.roi, 'cleanup')
        safe_call(IP.ImageProcessor, 'cleanup')
        safe_call(OCR.ImageOCR, 'cleanup')
        safe_call(BD.BreaknetDetection, 'cleanup')
        
        # 清理鍵盤監聽
        try:
            keyboard.unhook_all()
            print("已清理鍵盤監聽")
        except Exception as e:
            print(f"清理鍵盤監聽時發生錯誤: {e}")
        
        # 強制關閉所有 OpenCV 視窗
        try:
            cv.destroyAllWindows()
            # 等待視窗關閉
            for _ in range(10):
                cv.waitKey(1)
            print("已關閉所有 OpenCV 視窗")
        except Exception as e:
            print(f"關閉 OpenCV 視窗時發生錯誤: {e}")
        
        # 終止 scrcpy 進程
        if scrcpy_process:
            try:
                scrcpy_process.terminate()
                # 等待進程結束
                scrcpy_process.wait(timeout=3)
                print("已終止 scrcpy 進程")
            except subprocess.TimeoutExpired:
                # 如果進程沒有在指定時間內結束，強制殺死
                scrcpy_process.kill()
                print("已強制終止 scrcpy 進程")
            except Exception as e:
                print(f"終止 scrcpy 進程時發生錯誤: {e}")
        
        print("資源清理完成")
        
    except Exception as e:
        print(f"清理資源時發生錯誤: {e}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"主程式發生錯誤: {e}")
        cleanup_resources()
    finally:
        print("程式已退出")