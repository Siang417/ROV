import csv
import os
from datetime import datetime
import threading

class BreaknetDetection:
    # 類別屬性
    running = True
    debug_mode = False
    current_detection_surface = 1  # 當前選擇的檢測面 (1-5)
    csv_file_path = ""
    csv_lock = threading.Lock()  # 用於保護 CSV 文件寫入的線程鎖
    
    @classmethod
    def initialize(cls):
        """初始化破網檢測模組，創建 CSV 文件"""
        try:
            # 獲取當前日期，格式為 MMDD
            current_date = datetime.now().strftime("%m%d")
            
            # 創建文件名
            filename = f"破網檢測_{current_date}.csv"
            cls.csv_file_path = filename
            
            # 檢查文件是否已存在
            file_exists = os.path.exists(cls.csv_file_path)
            
            # 如果文件不存在，創建並寫入標題行
            if not file_exists:
                with open(cls.csv_file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['檢測面', '水深高度', '檢測時間'])
                print(f"已創建破網檢測記錄文件: {cls.csv_file_path}")
            else:
                print(f"使用現有的破網檢測記錄文件: {cls.csv_file_path}")
            
            print(f"當前選擇的檢測面: {cls.current_detection_surface}")
            print("使用按鍵 '1'-'5' 選擇檢測面，按 'b' 記錄當前水深")
            
            return True
            
        except Exception as e:
            print(f"初始化破網檢測模組失敗: {e}")
            return False
    
    @classmethod
    def set_detection_surface(cls, surface_number):
        """設置當前檢測面 (1-5)"""
        if 1 <= surface_number <= 5:
            cls.current_detection_surface = surface_number
            print(f"已選擇檢測面: {surface_number}")
            if cls.debug_mode:
                print(f"當前檢測面設置為: {cls.current_detection_surface}")
        else:
            print(f"無效的檢測面編號: {surface_number}，請使用 1-5")
    
    @classmethod
    def record_depth_measurement(cls, ocr_result):
        """記錄水深測量結果"""
        try:
            # 獲取當前時間，格式為 MM:SS (分鐘:秒)
            current_time = datetime.now()
            time_string = current_time.strftime("%M:%S")  # 分鐘:秒格式 MM:SS
            
            # 處理 OCR 結果
            depth_value = ocr_result.strip() if ocr_result else "無法識別"
            
            # 確保深度值包含單位
            if depth_value != "無法識別" and not depth_value.endswith('m'):
                if depth_value.replace('.', '').isdigit():
                    depth_value += "m"
            
            # 使用線程鎖保護文件寫入
            with cls.csv_lock:
                # 將記錄寫入 CSV 文件
                with open(cls.csv_file_path, 'a', newline='', encoding='utf-8-sig') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow([cls.current_detection_surface, depth_value, time_string])
            
            # 顯示記錄信息
            print(f"[記錄] 檢測面: {cls.current_detection_surface}, 水深: {depth_value}, 時間: {time_string}")
            
            if cls.debug_mode:
                print(f"記錄已保存到: {cls.csv_file_path}")
            
            return True
            
        except Exception as e:
            print(f"記錄水深測量失敗: {e}")
            return False
    
    @classmethod
    def get_current_surface(cls):
        """獲取當前選擇的檢測面"""
        return cls.current_detection_surface
    
    @classmethod
    def display_current_status(cls):
        """顯示當前狀態"""
        print(f"當前檢測面: {cls.current_detection_surface}")
        print(f"記錄文件: {cls.csv_file_path}")
        
        # 顯示文件中的記錄數量
        try:
            if os.path.exists(cls.csv_file_path):
                with open(cls.csv_file_path, 'r', encoding='utf-8-sig') as csvfile:
                    reader = csv.reader(csvfile)
                    rows = list(reader)
                    record_count = len(rows) - 1  # 減去標題行
                    print(f"已記錄數量: {record_count} 筆")
        except Exception as e:
            print(f"讀取記錄數量失敗: {e}")
    
    @classmethod
    def show_recent_records(cls, count=5):
        """顯示最近的記錄"""
        try:
            if not os.path.exists(cls.csv_file_path):
                print("記錄文件不存在")
                return
            
            with open(cls.csv_file_path, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)
                
                if len(rows) <= 1:  # 只有標題行或文件為空
                    print("暫無記錄")
                    return
                
                print(f"\n最近 {min(count, len(rows)-1)} 筆記錄:")
                print("-" * 40)
                print(f"{'檢測面':<8} {'水深高度':<12} {'檢測時間':<8}")
                print("-" * 40)
                
                # 顯示最近的記錄（從最後開始）
                recent_rows = rows[-count-1:-1] if len(rows) > count else rows[1:]
                for row in recent_rows[-count:]:
                    if len(row) >= 3:
                        print(f"{row[0]:<8} {row[1]:<12} {row[2]:<8}")
                print("-" * 40)
                
        except Exception as e:
            print(f"顯示最近記錄失敗: {e}")
    
    @classmethod
    def export_daily_summary(cls):
        """匯出當日統計摘要"""
        try:
            if not os.path.exists(cls.csv_file_path):
                print("記錄文件不存在")
                return
            
            with open(cls.csv_file_path, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)
                
                if len(rows) <= 1:
                    print("暫無記錄可統計")
                    return
                
                # 統計各檢測面的記錄數量
                surface_counts = {}
                total_records = 0
                
                for row in rows[1:]:  # 跳過標題行
                    if len(row) >= 3:
                        surface = row[0]
                        surface_counts[surface] = surface_counts.get(surface, 0) + 1
                        total_records += 1
                
                print(f"\n當日檢測統計摘要 ({datetime.now().strftime('%m/%d')}):")
                print("=" * 30)
                print(f"總記錄數: {total_records}")
                print("\n各檢測面記錄數:")
                for i in range(1, 6):
                    count = surface_counts.get(str(i), 0)
                    print(f"檢測面 {i}: {count} 筆")
                print("=" * 30)
                
        except Exception as e:
            print(f"匯出統計摘要失敗: {e}")
    
    @classmethod
    def toggle_debug_mode(cls):
        """切換調試模式"""
        cls.debug_mode = not cls.debug_mode
        print(f"破網檢測調試模式已 {'開啟' if cls.debug_mode else '關閉'}")
    
    @classmethod
    def cleanup(cls):
        """清理資源"""
        cls.running = False
        print("破網檢測模組已清理")
        
        # 顯示最終統計
        cls.export_daily_summary()