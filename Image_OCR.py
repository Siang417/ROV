import cv2 as cv
import numpy as np
import pytesseract
import threading
import time
from PIL import Image

class ImageOCR:
    # 類別屬性
    running = True
    ocr_active = False
    last_ocr_result = ""
    ocr_thread = None
    debug_mode = False
    
    # OCR 結果顯示相關
    result_window_name = "OCR 結果"
    result_image = None
    show_result_window = True
    
    @classmethod
    def perform_ocr_on_image(cls, processed_image):
        """對處理後的圖像執行 OCR - 使用 ADB_OCR_1.py 的標準配置"""
        if processed_image is None or processed_image.size == 0:
            if cls.debug_mode:
                print("OCR: 輸入圖像為空")
            return ""
        
        try:
            # 使用 ADB_OCR_1.py 的標準 OCR 配置 (PSM 6 為主要模式)
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789.m'
            
            # 執行 OCR
            ocr_result = pytesseract.image_to_string(processed_image, config=custom_config, lang='ROV')
            result = ocr_result.strip()
            
            if cls.debug_mode:
                print(f"OCR 結果: '{result}'")
            
            return result
            
        except Exception as e:
            if cls.debug_mode:
                print(f"OCR 處理失敗: {e}")
            return ""
    
    @classmethod
    def create_result_display_image(cls, processed_image, ocr_result):
        """創建顯示 OCR 結果的圖像"""
        try:
            # 確保圖像是 BGR 格式
            if len(processed_image.shape) == 2:
                display_img = cv.cvtColor(processed_image, cv.COLOR_GRAY2BGR)
            else:
                display_img = processed_image.copy()
            
            # 放大圖像以便更好地顯示
            height, width = display_img.shape[:2]
            if width < 400:
                scale = 400 / width
                new_width = int(width * scale)
                new_height = int(height * scale)
                display_img = cv.resize(display_img, (new_width, new_height), interpolation=cv.INTER_CUBIC)
            
            # 在圖像下方添加文字區域
            text_height = 80
            text_area = np.ones((text_height, display_img.shape[1], 3), dtype=np.uint8) * 255
            
            # 合併圖像和文字區域
            result_img = np.vstack([display_img, text_area])
            
            # 添加 OCR 結果文字
            font = cv.FONT_HERSHEY_SIMPLEX
            font_scale = 1.2
            color = (0, 0, 255)  # 紅色
            thickness = 2
            
            # 準備顯示的文字
            display_text = f"OCR: {ocr_result}" if ocr_result else "OCR: (無結果)"
            
            # 計算文字位置（置中）
            text_size = cv.getTextSize(display_text, font, font_scale, thickness)[0]
            text_x = (result_img.shape[1] - text_size[0]) // 2
            text_y = display_img.shape[0] + 50
            
            # 繪製文字
            cv.putText(result_img, display_text, (text_x, text_y), font, font_scale, color, thickness)
            
            # 添加時間戳
            timestamp = time.strftime("%H:%M:%S")
            time_text = f"Time: {timestamp}"
            cv.putText(result_img, time_text, (10, result_img.shape[0] - 10), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 1)
            
            return result_img
            
        except Exception as e:
            if cls.debug_mode:
                print(f"創建結果顯示圖像失敗: {e}")
            return processed_image
    
    @classmethod
    def display_ocr_result(cls, processed_image, ocr_result):
        """顯示 OCR 結果視窗"""
        if not cls.show_result_window:
            return
            
        try:
            # 創建結果顯示圖像
            result_img = cls.create_result_display_image(processed_image, ocr_result)
            cls.result_image = result_img
            
            # 創建並顯示視窗
            cv.namedWindow(cls.result_window_name, cv.WINDOW_NORMAL)
            cv.resizeWindow(cls.result_window_name, 500, 400)
            cv.imshow(cls.result_window_name, result_img)
            cv.waitKey(1)
            
            # 在控制台也輸出結果
            if ocr_result:
                print(f"[{time.strftime('%H:%M:%S')}] OCR 結果: {ocr_result}")
            
        except Exception as e:
            if cls.debug_mode:
                print(f"顯示 OCR 結果時出錯: {e}")
    
    @classmethod
    def start_ocr(cls, image_processor_class):
        """開始 OCR 處理線程"""
        cls.ocr_active = True
        cls.ocr_thread = threading.Thread(target=cls._ocr_worker, args=(image_processor_class,))
        cls.ocr_thread.daemon = True
        cls.ocr_thread.start()
        print("OCR 處理線程已啟動")
        print("OCR 結果將顯示在 'OCR 結果' 視窗中")
    
    @classmethod
    def stop_ocr(cls):
        """停止 OCR 處理"""
        cls.ocr_active = False
        if cls.ocr_thread and cls.ocr_thread.is_alive():
            cls.ocr_thread.join(timeout=1)
        cv.destroyWindow(cls.result_window_name)
        print("OCR 處理已停止")
    
    @classmethod
    def _ocr_worker(cls, image_processor_class):
        """OCR 工作線程"""
        while cls.running and cls.ocr_active:
            try:
                # 獲取最後處理的圖像
                processed_image = image_processor_class.get_last_processed_image()
                
                if processed_image is not None:
                    # 執行 OCR
                    ocr_result = cls.perform_ocr_on_image(processed_image)
                    
                    # 更新結果
                    cls.last_ocr_result = ocr_result
                    
                    # 顯示結果
                    cls.display_ocr_result(processed_image, ocr_result)
                
                time.sleep(0.3)  # 控制 OCR 處理頻率
                
            except Exception as e:
                if cls.debug_mode:
                    print(f"OCR 線程錯誤: {e}")
                time.sleep(0.5)
    
    @classmethod
    def test_ocr_on_image(cls, image):
        """測試單張圖像的 OCR"""
        if image is None or image.size == 0:
            print("沒有可用的圖像進行 OCR 測試")
            return
        
        try:
            # 使用標準配置測試
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789.m'
            result = pytesseract.image_to_string(image, config=custom_config, lang='ROV')
            
            print(f"OCR 測試結果: '{result.strip()}'")
            
            # 顯示測試結果
            cls.display_ocr_result(image, result.strip())
            
        except Exception as e:
            print(f"OCR 測試失敗: {e}")
    
    @classmethod
    def toggle_result_window(cls):
        """切換結果視窗顯示"""
        cls.show_result_window = not cls.show_result_window
        if not cls.show_result_window:
            cv.destroyWindow(cls.result_window_name)
            print("OCR 結果視窗已隱藏")
        else:
            print("OCR 結果視窗已顯示")
    
    @classmethod
    def get_last_result(cls):
        """獲取最後的 OCR 結果"""
        return cls.last_ocr_result
    
    @classmethod
    def toggle_debug_mode(cls):
        """切換調試模式"""
        cls.debug_mode = not cls.debug_mode
        print(f"OCR 調試模式已 {'開啟' if cls.debug_mode else '關閉'}")
    
    @classmethod
    def cleanup(cls):
        """清理資源"""
        cls.running = False
        cls.ocr_active = False
        
        try:
            # 安全地銷毀視窗
            if hasattr(cls, 'result_window_name') and cls.result_window_name:
                # 檢查視窗是否存在
                try:
                    # 先嘗試獲取視窗屬性，如果視窗不存在會拋出異常
                    cv.getWindowProperty(cls.result_window_name, cv.WND_PROP_VISIBLE)
                    cv.destroyWindow(cls.result_window_name)
                except cv.error:
                    # 視窗不存在，忽略錯誤
                    pass
            
            # 銷毀所有 OpenCV 視窗
            cv.destroyAllWindows()
            
        except Exception as e:
            print(f"OCR 清理過程中發生錯誤: {e}")
        
        print("OCR 模組已清理") 