import cv2 as cv
import numpy as np
from PIL import ImageGrab
import time
import threading
from datetime import datetime
import os

class ImageProcessor:
    # 類別屬性
    running = True
    processing_active = False
    last_processed_image = None
    window_name = "ROI 影像處理結果"
    debug_mode = False
    
    # 資料集保存路徑
    DATASET_DIR = r"C:\Users\Zz423\Desktop\研究所\UCL\水下無人機\角度抓取測試\dataset"
    RAW_DIR = os.path.join(DATASET_DIR, "raw")
    PROCESSED_DIR = os.path.join(DATASET_DIR, "processed")
    
    @classmethod
    def create_dataset_directories(cls):
        """創建用於保存資料集的目錄"""
        for dir_path in [cls.DATASET_DIR, cls.RAW_DIR, cls.PROCESSED_DIR]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                print(f"已創建目錄: {dir_path}")
    
    @classmethod
    def save_to_dataset(cls, raw_image, processed_image):
        """保存原始和處理後的圖像到資料集"""
        try:
            # 生成時間戳作為文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            
            # 保存原始圖像
            raw_path = os.path.join(cls.RAW_DIR, f"raw_{timestamp}.png")
            cv.imwrite(raw_path, raw_image)
            
            # 保存處理後圖像
            processed_path = os.path.join(cls.PROCESSED_DIR, f"processed_{timestamp}.png")
            cv.imwrite(processed_path, processed_image)
            
            if cls.debug_mode:
                print(f"已保存圖像到資料集: {raw_path} 和 {processed_path}")
        except Exception as e:
            print(f"保存圖像到資料集時出錯: {e}")
    
    @classmethod
    def preprocess_for_digits(cls, image):
        """針對水下攝影界面數字的預處理 - 使用 ADB_OCR_1.py 的標準流程"""
        
        # 轉換為灰度圖
        if len(image.shape) == 3:
            gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # 放大圖像以提高 OCR 準確性
        height, width = gray.shape
        scale_factor = 5
        enlarged = cv.resize(gray, (width * scale_factor, height * scale_factor), interpolation=cv.INTER_CUBIC)
        
        # 高斯模糊去噪
        blurred = cv.GaussianBlur(enlarged, (3, 3), 0)
        
        # 雙邊濾波器保持邊緣清晰
        bilateral = cv.bilateralFilter(blurred, 9, 75, 75)
        
        # CLAHE 對比度限制自適應直方圖均衡化
        clahe = cv.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(bilateral)
        
        # 雙重二值化處理
        _, binary1 = cv.threshold(enhanced, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)
        _, binary2 = cv.threshold(enhanced, 180, 255, cv.THRESH_BINARY)
        
        # 合併兩種二值化結果
        combined_binary = cv.bitwise_or(binary1, binary2)
        
        # 形態學處理
        kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (2, 2))
        morphed = cv.morphologyEx(combined_binary, cv.MORPH_CLOSE, kernel)
        
        # 輪廓過濾，移除小噪點
        contours, _ = cv.findContours(morphed, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        mask = np.zeros_like(morphed)
        for contour in contours:
            area = cv.contourArea(contour)
            if area > 50:  # 只保留面積大於 50 的輪廓
                cv.drawContours(mask, [contour], -1, 255, -1)
        
        # 應用遮罩
        final_binary = cv.bitwise_and(morphed, mask)
        
        return final_binary
    
    @classmethod
    def process_image(cls, image):
        """處理圖像並返回結果"""
        if image is None or image.size == 0:
            print("錯誤: 輸入圖像為空")
            return None
        
        # 添加調試信息
        if cls.debug_mode:
            print(f"處理圖像: 形狀={image.shape}, 類型={image.dtype}")
        
        try:
            # 使用標準預處理方法
            processed_image = cls.preprocess_for_digits(image)
            
            # 保存到資料集
            cls.save_to_dataset(image, processed_image)
            
            # 更新最後處理的圖像
            cls.last_processed_image = processed_image.copy()
            
            if cls.debug_mode:
                print(f"處理完成: 形狀={processed_image.shape}, 類型={processed_image.dtype}")
                # 保存調試圖像
                cv.imwrite('debug_roi.png', image)
                cv.imwrite('debug_processed.png', processed_image)
                print("已保存調試圖像")
            
            return processed_image
            
        except Exception as e:
            print(f"圖像處理失敗: {e}")
            return None
    
    @classmethod
    def start_processing(cls, roi_module):
        """開始處理 ROI 區域影像的線程"""
        cls.processing_active = True
        cls.create_dataset_directories()  # 創建資料集目錄
        # 創建並啟動處理線程
        processing_thread = threading.Thread(target=cls._processing_worker, args=(roi_module,))
        processing_thread.daemon = True
        processing_thread.start()
        print("圖像處理線程已啟動")
    
    @classmethod
    def stop_processing(cls):
        """停止處理"""
        cls.processing_active = False
        print("圖像處理已停止")
    
    @classmethod
    def _processing_worker(cls, roi_module):
        """處理 ROI 區域影像的工作線程"""
        while cls.running and cls.processing_active:
            try:
                # 檢查是否有選擇完成的 ROI
                if not roi_module.roi.selection_complete:
                    time.sleep(0.1)
                    continue
                
                # 獲取當前截圖
                if roi_module.roi.scrcpy_window is None:
                    roi_module.roi.find_scrcpy_window()
                    time.sleep(1)
                    continue
                
                # 截取 scrcpy 視窗
                left, top = roi_module.roi.scrcpy_window.left, roi_module.roi.scrcpy_window.top
                width, height = roi_module.roi.scrcpy_window.width, roi_module.roi.scrcpy_window.height
                
                screenshot = ImageGrab.grab(bbox=(left, top, left + width, top + height))
                screenshot_np = np.array(screenshot)
                screenshot_np = cv.cvtColor(screenshot_np, cv.COLOR_RGB2BGR)
                
                # 提取 ROI 區域
                roi_image = screenshot_np[roi_module.roi.y_min:roi_module.roi.y_max, 
                                        roi_module.roi.x_min:roi_module.roi.x_max]
                
                if roi_image.size == 0:
                    time.sleep(0.1)
                    continue
                
                # 處理圖像
                processed_image = cls.process_image(roi_image)
                
                if processed_image is not None:
                    # 顯示處理結果
                    cls.display_processed_image(processed_image)
                
                time.sleep(0.1)  # 控制處理頻率
                
            except Exception as e:
                if cls.debug_mode:
                    print(f"處理線程錯誤: {e}")
                time.sleep(0.5)
    
    @classmethod
    def display_processed_image(cls, processed_image):
        """顯示處理後的圖像"""
        try:
            # 如果是灰度圖，轉換為 BGR 以便顯示
            if len(processed_image.shape) == 2:
                display_img = cv.cvtColor(processed_image, cv.COLOR_GRAY2BGR)
            else:
                display_img = processed_image
            
            # 創建視窗並顯示
            cv.namedWindow(cls.window_name, cv.WINDOW_NORMAL)
            cv.resizeWindow(cls.window_name, 400, 300)
            cv.imshow(cls.window_name, display_img)
            cv.waitKey(1)
            
        except Exception as e:
            if cls.debug_mode:
                print(f"顯示圖像時出錯: {e}")
    
    @classmethod
    def toggle_debug_mode(cls):
        """切換調試模式"""
        cls.debug_mode = not cls.debug_mode
        print(f"圖像處理調試模式已 {'開啟' if cls.debug_mode else '關閉'}")
    
    @classmethod
    def get_last_processed_image(cls):
        """獲取最後處理的圖像"""
        return cls.last_processed_image
    
    @classmethod
    def cleanup(cls):
        """清理資源"""
        cls.running = False
        cls.processing_active = False
        cv.destroyAllWindows()
        print("圖像處理模組已清理")