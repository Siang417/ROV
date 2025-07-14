import pygetwindow as gw
import time
import pyautogui
import numpy as np
import cv2 as cv
import keyboard
from PIL import Image, ImageGrab

class roi:
    # 類別屬性
    running = True
    debug_mode = False
    mouse_x, mouse_y = 0, 0
    processed_result = ""
    selection_image = None
    selection_complete = False
    x_min, y_min, x_max, y_max = 0, 0, 0, 0
    selecting = False
    scrcpy_window = None
    last_processed_roi = None
    last_processed_binary = None
    scrcpy_process = None
    last_window_debug = 0

    @classmethod
    def keyboard_worker(cls):
        """全局鍵盤監聽工作線程"""
        
        # 設置按鍵處理函數
        keyboard.on_press_key('s', lambda _: cls.select_roi_from_screenshot())  #按下s:選擇ROI區域
        keyboard.on_press_key('r', lambda _: cls.reset_selection())             #按下r:重製ROI區域
        keyboard.on_press_key('q', lambda _: cls.stop_application())            #按下q:退出程式
        keyboard.on_press_key('d', lambda _: cls.toggle_alternative_method())   #按下d:切換處理方法
        
        print("全局按鍵設置完成:")
        print("- 按 's' 鍵進入選擇模式")
        print("- 按 'r' 鍵重置選擇區域")
        print("- 按 'q' 鍵退出程式")
        print("- 按 'd' 鍵顯示處理結果")
        
        while cls.running:
            time.sleep(0.1)

    @classmethod
    def toggle_underwater_mode(cls):
        """切換海底處理模式"""
        # 假設我們在 OCR 模組中添加了一個標誌
        import Image_OCR as OCR
        OCR.ImageOCR.force_underwater_mode = not getattr(OCR.ImageOCR, 'force_underwater_mode', False)
        mode = "開啟" if OCR.ImageOCR.force_underwater_mode else "關閉"
        print(f"海底處理模式已{mode}")

    @classmethod
    def toggle_alternative_method(cls):
        """切換使用第二種處理方法"""
        if hasattr(cls, 'image_processor') and cls.image_processor is not None:
            cls.image_processor.use_alternative_method = not cls.image_processor.use_alternative_method
            print(f"切換至{'第二種' if cls.image_processor.use_alternative_method else '第一種'}一般處理方法")
            if hasattr(cls.image_processor, 'display_intermediate_results'):
                cls.image_processor.display_intermediate_results()
        else:
            print("警告: image_processor 未初始化，無法切換處理方法")


    @classmethod
    def display_processing_results(cls):
        """顯示處理結果"""
        import Image_Process as IP
        
        try:
            # 檢查是否有 display_intermediate_results 方法
            if hasattr(IP.ImageProcessor, 'display_intermediate_results'):
                IP.ImageProcessor.display_intermediate_results()
            else:
                print("未找到 display_intermediate_results 方法")
            
            # 檢查是否有 display_underwater_results 方法
            if hasattr(IP.ImageProcessor, 'display_underwater_results'):
                IP.ImageProcessor.display_underwater_results()
            else:
                print("未找到 display_underwater_results 方法")
            
            # 如果兩個方法都不存在，則顯示最後處理的二值化影像
            if (not hasattr(IP.ImageProcessor, 'display_intermediate_results') and 
                not hasattr(IP.ImageProcessor, 'display_underwater_results')):
                if IP.ImageProcessor.last_processed_binary is not None:
                    cv.namedWindow("最後處理結果", cv.WINDOW_NORMAL)
                    cv.imshow("最後處理結果", IP.ImageProcessor.last_processed_binary)
                    cv.waitKey(1)
                else:
                    print("沒有可用的處理結果")
        except Exception as e:
            print(f"顯示處理結果時發生錯誤: {e}")
    
    @classmethod
    def process_frame(cls, frame):
        """處理當前幀並提取 ROI 區域"""
        # 複製原始幀
        cls.original_frame = frame.copy()
        
        # 如果已選擇 ROI 區域
        if cls.selection_complete:
            # 提取 ROI 區域
            roi_region = cls.original_frame[cls.y_min:cls.y_max, cls.x_min:cls.x_max]
            cls.last_processed_roi = roi_region.copy()
            
            try:
                # 根據當前設置選擇處理方法
                if hasattr(cls, 'image_processor') and cls.image_processor is not None:
                    if hasattr(cls.image_processor, 'use_alternative_method') and cls.image_processor.use_alternative_method:
                        print("使用第二種一般處理方式")
                        cls.binary_image = cls.image_processor.process_image_alternative(roi_region)
                    else:
                        print("使用第一種一般處理方式")
                        cls.binary_image = cls.image_processor.process_image(roi_region)
                    
                    # 更新處理結果 - 保存到 image_processor 實例
                    cls.last_processed_binary = cls.binary_image
                    cls.image_processor.last_processed_binary = cls.binary_image
                else:
                    print("警告: image_processor 未初始化")
                    
            except Exception as e:
                print(f"處理 ROI 影像時發生錯誤: {e}")
        
        # 在原始幀上繪製 ROI 框
        cls.draw_roi_on_frame()
        
        return cls.original_frame

    @classmethod
    def find_scrcpy_window(cls):
        """查找 scrcpy 視窗"""
        
        # 獲取所有視窗
        all_windows = gw.getAllWindows()
        
        # 尋找 scrcpy 視窗 (包含手機型號標識)
        for win in all_windows:
            if 'scrcpy' in win.title.lower() or 'SM-' in win.title:
                cls.scrcpy_window = win
                print(f"找到 scrcpy 視窗: {win.title}")
                return cls.scrcpy_window
                
        # 如果沒有找到，則輸出所有視窗標題以供調試
        if cls.scrcpy_window is None and time.time() - cls.last_window_debug > 10:
            print("所有視窗標題:")
            for win in all_windows:
                print(f"- {win.title}")
            cls.last_window_debug = time.time()
        
        return cls.scrcpy_window

    @classmethod
    def select_roi_from_screenshot(cls):
        """從截圖中選擇 ROI"""
        
        print("正在進入選擇模式...")
        
        if cls.scrcpy_window is None:
            print("未找到 scrcpy 視窗，嘗試重新查找...")
            cls.find_scrcpy_window()
            if cls.scrcpy_window is None:
                print("仍未找到 scrcpy 視窗，無法進行選擇")
                return
        
        try:
            # 獲取 scrcpy 視窗的位置和大小
            left, top = cls.scrcpy_window.left, cls.scrcpy_window.top
            width, height = cls.scrcpy_window.width, cls.scrcpy_window.height
            
            print(f"已截取 scrcpy 視窗畫面，大小: {width}x{height}")
            
            # 截取整個 scrcpy 視窗
            screenshot = ImageGrab.grab(bbox=(left, top, left + width, top + height))
            screenshot_np = np.array(screenshot)
            screenshot_np = cv.cvtColor(screenshot_np, cv.COLOR_RGB2BGR)
            
            # 保存截圖
            cls.selection_image = screenshot_np.copy()
            
            # 創建選擇視窗
            window_name = "選擇 ROI 區域 (拖曳選擇，按 Enter 確認，按 Esc 取消)"
            cv.namedWindow(window_name, cv.WINDOW_NORMAL)
            
            # 使用 OpenCV 的 selectROI 函數
            rect = cv.selectROI(window_name, cls.selection_image, fromCenter=False, showCrosshair=True)
            
            # 關閉選擇視窗
            cv.destroyWindow(window_name)
            
            # 獲取選擇的坐標
            cls.x_min, cls.y_min, w, h = rect
            cls.x_max, cls.y_max = cls.x_min + w, cls.y_min + h
            
            # 如果選擇了有效區域
            if w > 0 and h > 0:
                cls.selection_complete = True
                print(f"已選擇區域: ({cls.x_min}, {cls.y_min}) - ({cls.x_max}, {cls.y_max})")
            else:
                print("取消選擇")
        
        except Exception as e:
            print(f"選擇區域錯誤: {e}")

    @classmethod
    def reset_selection(cls):
        """重置選擇區域"""
        
        cls.selection_complete = False
        cls.x_min, cls.y_min, cls.x_max, cls.y_max = 0, 0, 0, 0
        print("已重置選擇區域")    
    
    @classmethod
    def stop_application(cls):
        """停止應用程式"""
        
        cls.running = False
        print("準備退出程式...")
        cv.destroyAllWindows()

    @classmethod
    def cleanup(cls):
        """清理資源"""
        cls.running = False
        cls.selection_mode = False
        cls.selection_active = False
        
        # 關閉相關視窗
        try:
            if hasattr(cls, 'selection_image') and cls.selection_image is not None:
                cv.destroyWindow("ROI Selection")
        except:
            pass
        
        try:
            cv.destroyWindow("Processing Result")
        except:
            pass
        
        print("ROI 模組已清理")

    @classmethod
    def main(cls):
        """主程式入口點"""
        print("ROI 選擇工具啟動中...")
        
        # 設置鍵盤監聽
        cls.keyboard_worker()
        
        print("程式已退出")

if __name__ == "__main__":
    # 單元測試
    import unittest
    import threading
    import os
    
    class TestROI(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            # 創建一個模擬的 scrcpy 視窗 (用於測試)
            # 在實際環境中可能需要啟動真實的 scrcpy 或模擬視窗
            print("設置測試環境...")
            
            # 啟動鍵盤監聽線程
            cls.keyboard_thread = threading.Thread(target=ROI.keyboard_worker)
            cls.keyboard_thread.daemon = True
            cls.keyboard_thread.start()
            
        def test_find_window(self):
            """測試查找視窗功能"""
            # 由於可能沒有真實的 scrcpy 視窗，這裡只測試函數不會崩潰
            try:
                window = ROI.find_scrcpy_window()
                # 如果找不到視窗，測試仍然通過，但會輸出提示
                if window is None:
                    print("警告: 未找到 scrcpy 視窗，但測試繼續進行")
            except Exception as e:
                self.fail(f"find_scrcpy_window() 拋出異常: {e}")
                
        def test_reset_selection(self):
            """測試重置選擇功能"""
            # 設置初始值
            ROI.x_min, ROI.y_min = 10, 20
            ROI.x_max, ROI.y_max = 100, 200
            ROI.selection_complete = True
            
            # 呼叫重置函數
            ROI.reset_selection()
            
            # 驗證結果
            self.assertEqual(ROI.x_min, 0)
            self.assertEqual(ROI.y_min, 0)
            self.assertEqual(ROI.x_max, 0)
            self.assertEqual(ROI.y_max, 0)
            self.assertFalse(ROI.selection_complete)
            
        def test_stop_application(self):
            """測試停止應用程式功能"""
            # 設置初始值
            ROI.running = True
            
            # 呼叫停止函數
            ROI.stop_application()
            
            # 驗證結果
            self.assertFalse(ROI.running)
            
        @classmethod
        def tearDownClass(cls):
            # 清理測試環境
            print("清理測試環境...")
            ROI.running = False
            # 等待線程結束
            if hasattr(cls, 'keyboard_thread') and cls.keyboard_thread.is_alive():
                cls.keyboard_thread.join(1.0)  # 等待最多 1 秒
    
    # 運行單元測試
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
    
    # 如果不是在測試模式下，運行主程式
    if os.environ.get('PYTEST_CURRENT_TEST') is None:
        print("\n開始運行主程式...")
        ROI.main()
