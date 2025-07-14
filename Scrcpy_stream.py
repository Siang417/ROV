import subprocess
import os
import cv2
import numpy as np
import time

class stream:
    def start_adb_server():
        """啟動 ADB 伺服器"""
        os.system("adb start-server")
        print("ADB 伺服器已啟動")

    def check_devices():
        """檢查是否有設備連接"""
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        devices = result.stdout.strip().split('\n')
        if len(devices) <= 1:  # 第一行是標題
            print("未找到設備，請確保手機已連接並啟用 USB 偵錯")
            return None
        device_id = devices[1].split('\t')[0]
        print(f"已連接設備：{device_id}")
        return device_id

    def start_scrcpy_server(device_id, port=27183):
        """啟動 scrcpy 伺服器模式，將畫面串流到本地端口"""
        try:
            # 啟動 scrcpy 伺服器，禁用視窗顯示，僅串流
            cmd = [
                "scrcpy",
                "-s", device_id,  # 指定設備
                "--no-display",   # 不顯示視窗
                "--video-port", str(port),  # 指定串流端口
                "--video-codec", "h264"  # 使用 H264 編碼
            ]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(2)  # 等待伺服器啟動
            print(f"scrcpy 伺服器已啟動，串流端口：{port}")
            return process
        except Exception as e:
            print(f"啟動 scrcpy 伺服器失敗：{e}")   
            return None

    def connect_to_stream(port=27183):
        """連接到 scrcpy 串流（這裡僅為示範，實際需要解析 H264 串流）"""
        print("注意：直接從 scrcpy 串流擷取畫面需要進階處理（H264 解碼）。")
        print("此程式碼僅啟動 scrcpy 伺服器，畫面擷取部分需進一步開發。")
        # 這裡可以進一步使用 ffplay 或其他工具播放串流，例如：
        # subprocess.run(["ffplay", f"tcp://127.0.0.1:{port}"])
        return None

    def start_scrcpy_window(device_id):
        """啟動 scrcpy 視窗模式"""
        try:
            # 啟動 scrcpy 視窗
            cmd = [
                "scrcpy",
                "-s", device_id,  # 指定設備
                "--window-title", f"scrcpy-{device_id}"  # 設置視窗標題
            ]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("已啟動 scrcpy 視窗")
            return process
        except Exception as e:
            print(f"啟動 scrcpy 視窗時發生錯誤: {e}")
            return None

    def main():
        stream.start_adb_server()
        device_id = stream.check_devices()
        if not device_id:
            return
        
        # 啟動 scrcpy 視窗模式
        scrcpy_process = subprocess.Popen(["scrcpy", "-s", device_id], 
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE)
        return scrcpy_process
      
if __name__ == "__main__":
    stream.main()
