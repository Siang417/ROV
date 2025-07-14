import sys
import Scrcpy_stream as scrcpy
import Get_ROI as ROI
import Image_Process as IP  # 導入新模組
import cv2 as cv
import numpy as np
import time
import threading
import pygetwindow as gw
import Image_OCR as OCR

def main():
    """主程式入口點"""
    print("啟動 Android 畫面擷取與 ROI 選擇工具...")
    
    # 啟用偵錯模式
    ROI.roi.debug_mode = True
    IP.ImageProcessor.debug_mode = True
    OCR.ImageOCR.debug_mode = True
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
            "-s", device_id,  # 指定設備
            "--window-title", f"scrcpy-{device_id}"  # 設置視窗標題
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
    for _ in range(5):  # 嘗試幾次
        ROI.roi.find_scrcpy_window()
        if ROI.roi.scrcpy_window is not None:
            found_window = True
            break
        time.sleep(1)
    
    if not found_window:
        print("無法找到 scrcpy 視窗，請確保 scrcpy 已正確啟動")
        return
    
    # 啟動影像處理線程
    image_processing_thread = IP.ImageProcessor.start_processing(ROI)

    # 啟動 OCR 處理模組
    ocr_thread = OCR.ImageOCR.start_ocr(IP.ImageProcessor)
    
    # 啟動鍵盤監聽
    print("\n請使用以下按鍵操作:")
    print("- 按 's' 鍵進入選擇模式")
    print("- 按 'r' 鍵重置選擇區域")
    print("- 按 'd' 鍵切換處理方法")
    print("- 按 'q' 鍵退出程式")
    print("- 按 'o' 鍵切換 OCR 結果視窗")
    print("- 按 't' 鍵切換 OCR 調試模式")

    # 添加 'p' 鍵功能
    import keyboard
    keyboard.on_press_key('p', lambda _: IP.ImageProcessor.save_processed_image())
    keyboard.on_press_key('d', lambda _: IP.ImageProcessor.display_intermediate_results())
    keyboard.add_hotkey('o', lambda: OCR.ImageOCR.toggle_result_window())  # 新增：切換 OCR 視窗
    keyboard.add_hotkey('t', lambda: OCR.ImageOCR.toggle_debug_mode())     # 新增：切換 OCR 調試模式

    
    # 啟動鍵盤監聽
    ROI.roi.keyboard_worker()
    
    # 清理資源
    IP.ImageProcessor.stop_processing()
    cv.destroyAllWindows()
    if scrcpy_process:
        scrcpy_process.terminate()
    print("程式已退出")

# 保持原有的 draw_roi_on_window 函數
def draw_roi_on_window():
    """在 scrcpy 視窗上繪製 ROI 框"""
    window_name = "ROI 顯示"
    cv.namedWindow(window_name, cv.WINDOW_NORMAL)
    
    while ROI.roi.running:
        # 檢查是否已選擇 ROI 且 scrcpy 視窗存在
        if ROI.roi.selection_complete and ROI.roi.scrcpy_window is not None:
            try:
                # 獲取視窗位置和大小
                left, top = ROI.roi.scrcpy_window.left, ROI.roi.scrcpy_window.top
                width, height = ROI.roi.scrcpy_window.width, ROI.roi.scrcpy_window.height
                
                # 截取視窗畫面
                screenshot = ROI.ImageGrab.grab(bbox=(left, top, left + width, top + height))
                screenshot_np = np.array(screenshot)
                screenshot_np = cv.cvtColor(screenshot_np, cv.COLOR_RGB2BGR)
                
                # 繪製矩形框
                x_min, y_min = ROI.roi.x_min, ROI.roi.y_min
                x_max, y_max = ROI.roi.x_max, ROI.roi.y_max
                
                # 確保座標在有效範圍內
                x_min = max(0, min(x_min, width-1))
                y_min = max(0, min(y_min, height-1))
                x_max = max(0, min(x_max, width-1))
                y_max = max(0, min(y_max, height-1))
                
                # 繪製矩形
                cv.rectangle(screenshot_np, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
                
                # 設置視窗大小與 scrcpy 視窗完全一致
                cv.resizeWindow(window_name, width, height)
                
                # 顯示圖像
                cv.imshow(window_name, screenshot_np)
                cv.waitKey(100)  # 短暫顯示，然後更新
            except Exception as e:
                print(f"繪製 ROI 時發生錯誤: {e}")
                time.sleep(1)
        else:
            time.sleep(0.5)

if __name__ == "__main__":
    main()
