import cv2
import numpy as np
import pyautogui
import pygetwindow as gw
import time
from PIL import Image
import pytesseract
import argparse
import sys
import threading
import tkinter as tk
from tkinter import ttk

# 設定 tesseract 執行檔路徑（請依實際安裝路徑修改）
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def find_image_on_screen(template_path, threshold=0.8, screenshot_img=None):
    # 若有傳入螢幕截圖則直接用，否則自己截圖
    if screenshot_img is None:
        screenshot_img = pyautogui.screenshot()
    screenshot = cv2.cvtColor(np.array(screenshot_img), cv2.COLOR_RGB2BGR)
    template = cv2.imread(template_path, cv2.IMREAD_COLOR)
    res = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    loc = np.where(res >= threshold)
    points = list(zip(*loc[::-1]))
    if points:
        return points[0]  # 回傳第一個找到的位置 (x, y)
    return None


def bring_window_to_front(window_title, retry=1, delay=0.5):
    windows = gw.getWindowsWithTitle(window_title)
    if not windows:
        print(f"找不到視窗: {window_title}")
        return False
    win = windows[0]
    for i in range(retry):
        try:
            if not win.isActive:
                win.activate()
                time.sleep(delay)  # 等待視窗彈出
            return True
        except Exception as e:
            print(f"bring_window_to_front activate 失敗, retry {i+1}/{retry}: {e}")
            time.sleep(delay)
    print("bring_window_to_front activate 多次失敗")
    return False


def get_window_relative_screenshot(win_left, win_top, region, screenshot_img=None):
    x1, y1, x2, y2 = region
    abs_left = int(win_left + x1)
    abs_top = int(win_top + y1)
    width = int(x2 - x1)
    height = int(y2 - y1)
    if screenshot_img is not None:
        # 從已擷取的螢幕圖像裁切
        img_np = np.array(screenshot_img)
        crop = img_np[abs_top:abs_top+height, abs_left:abs_left+width]
        return Image.fromarray(crop)
    else:
        screenshot = pyautogui.screenshot(region=(abs_left, abs_top, width, height))
        return screenshot


def get_fixed_area_screenshot(region, win_left, win_top, screenshot_img=None):
    x1, y1, x2, y2 = region
    abs_x1 = win_left + x1
    abs_y1 = win_top + y1
    width = int(x2 - x1)
    height = int(y2 - y1)
    if screenshot_img is not None:
        img_np = np.array(screenshot_img)
        crop = img_np[abs_y1:abs_y1+height, abs_x1:abs_x1+width]
        return Image.fromarray(crop)
    else:
        screenshot = pyautogui.screenshot(region=(abs_x1, abs_y1, width, height))
        return screenshot


def ocr_number_from_image(image):
    # 針對 [數字/數字] 圖片特徵做預處理
    gray = image.convert("L")
    # 提高對比
    bw = gray.point(lambda x: 0 if x < 180 else 255, "1")
    # 裁切左右空白
    np_img = np.array(bw)
    cols = np.where(np_img.min(axis=0) < 255)[0]
    if cols.size > 0:
        bw = bw.crop((cols[0], 0, cols[-1]+1, bw.height))
    # 只允許數字和斜線
    custom_config = r'--psm 7 -c tessedit_char_whitelist=0123456789/'
    text = pytesseract.image_to_string(bw, config=custom_config)
    # 只取第一個 [數字/數字] 格式
    import re
    match = re.search(r"\[(\d+)\s*/\s*(\d+)\]", text)
    if match:
        return match.group(1), match.group(2)
    # 若沒括號，嘗試直接找數字/數字
    match2 = re.search(r"(\d+)\s*/\s*(\d+)", text)
    if match2:
        return match2.group(1), match2.group(2)
    # 若都找不到，回傳原始辨識字串
    return text.strip(), None


def check_buff_status(buff_region, win_left, win_top, screenshot_img, buff_template_path='buff.png', threshold=0.6):
    x1, y1, x2, y2 = buff_region
    abs_x1 = win_left + x1
    abs_y1 = win_top + y1
    width = int(x2 - x1)
    height = int(y2 - y1)
    # 擷取buff區域
    if screenshot_img is not None:
        img_np = np.array(screenshot_img)
        crop = img_np[abs_y1:abs_y1+height, abs_x1:abs_x1+width]
        buff_area = crop
    else:
        buff_area = np.array(pyautogui.screenshot(region=(abs_x1, abs_y1, width, height)))
    # 儲存 buff 區域圖檔方便 debug
    debug_buff_img = Image.fromarray(buff_area)
    debug_buff_img.save("debug_buff_area.png")
    # 讀取buff範本
    buff_template = cv2.imread(buff_template_path, cv2.IMREAD_COLOR)
    if buff_template is None:
        print(f"找不到 buff 範本圖片: {buff_template_path}")
        return False
    buff_area_bgr = cv2.cvtColor(buff_area, cv2.COLOR_RGB2BGR)
    # 轉灰階以減少顏色誤差影響
    buff_area_gray = cv2.cvtColor(buff_area_bgr, cv2.COLOR_BGR2GRAY)
    buff_template_gray = cv2.cvtColor(buff_template, cv2.COLOR_BGR2GRAY)
    # 若範本比區塊大，自動縮小範本到區塊內
    if (buff_template_gray.shape[0] > buff_area_gray.shape[0] or
            buff_template_gray.shape[1] > buff_area_gray.shape[1]):
        scale_y = buff_area_gray.shape[0] / buff_template_gray.shape[0]
        scale_x = buff_area_gray.shape[1] / buff_template_gray.shape[1]
        scale = min(scale_x, scale_y)
        new_size = (max(1, int(buff_template_gray.shape[1] * scale)), max(1, int(buff_template_gray.shape[0] * scale)))
        buff_template_gray = cv2.resize(buff_template_gray, new_size, interpolation=cv2.INTER_AREA)
        print(f"已將buff範本縮放為: {buff_template_gray.shape}")
    # 檢查範本尺寸是否大於區塊，避免cv2.matchTemplate錯誤
    if (buff_area_gray.shape[0] < buff_template_gray.shape[0] or
            buff_area_gray.shape[1] < buff_template_gray.shape[1]):
        print("buff區域比範本還小，無法比對")
        print(f"buff_area_gray.shape={buff_area_gray.shape}, buff_template_gray.shape={buff_template_gray.shape}")
        return False
    res = cv2.matchTemplate(buff_area_gray, buff_template_gray, cv2.TM_CCOEFF_NORMED)
    loc = np.where(res >= threshold)
    found = len(list(zip(*loc[::-1]))) > 0
    return found


def auto_insert_loop(get_keys_func, stop_event, running_func, interval_sec_func):
    # 等待主線程啟動與GUI初始化
    while not running_func():
        if stop_event.is_set():
            return
        time.sleep(0.1)
    first = True
    while running_func() and not stop_event.is_set():
        if first:
            first = False
            time.sleep(0.3)  # 確保第一次進入時有短暫延遲
        else:
            interval = max(1, interval_sec_func())
            for _ in range(int(interval * 10)):  # 每0.1秒檢查一次
                if not running_func() or stop_event.is_set():
                    return
                time.sleep(0.1)
        keys = get_keys_func()
        for key in keys:
            print(f"自動按鍵: {key}")
            try:
                import pyautogui
                pyautogui.keyDown(key)
                time.sleep(0.05)
                pyautogui.keyUp(key)
            except Exception as e:
                print(f"自動按鍵 {key} 發生錯誤: {e}")
            time.sleep(1)  # 每個按鍵之間稍作延遲


class AutoPotionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Potion GUI")
        self.running = False
        self.hp_threshold = tk.IntVar(value=150)
        self.mp_threshold = tk.IntVar(value=20)
        self.status_var = tk.StringVar(value="狀態: 停止")
        self.thread = None
        self.auto_insert_thread = None
        self.stop_event = threading.Event()
        self.focus_check_interval = 500  # ms
        self.focused = False

        # 客製化按鍵
        self.hp_key = tk.StringVar(value="end")
        self.mp_key = tk.StringVar(value="delete")
        self.insert_key = tk.StringVar(value="insert")
        self._waiting_key = None  # 用於記錄目前等待哪個按鍵
        self._waiting_key_idx = None  # 新增：記錄等待哪個buff鍵

        self.insert_keys = [tk.StringVar(value="1,2")]  # 預設多個buff鍵用逗號分隔

        self.buff_interval = tk.IntVar(value=200)

        self.root.after(self.focus_check_interval, self.check_focus_and_toggle)

        ttk.Label(root, text="HP 閾值:").grid(row=0, column=0, sticky="e")
        ttk.Entry(root, textvariable=self.hp_threshold, width=8).grid(row=0, column=1)
        ttk.Label(root, text="MP 閾值:").grid(row=1, column=0, sticky="e")
        ttk.Entry(root, textvariable=self.mp_threshold, width=8).grid(row=1, column=1)

        # 客製化按鍵設定區塊
        ttk.Label(root, text="HP 補品鍵:").grid(row=0, column=2, sticky="e")
        self.hp_key_entry = ttk.Entry(root, textvariable=self.hp_key, width=8)
        self.hp_key_entry.grid(row=0, column=3)
        self.hp_key_entry.bind("<Button-1>", lambda e: self.wait_for_key("hp"))

        ttk.Label(root, text="MP 補品鍵:").grid(row=1, column=2, sticky="e")
        self.mp_key_entry = ttk.Entry(root, textvariable=self.mp_key, width=8)
        self.mp_key_entry.grid(row=1, column=3)
        self.mp_key_entry.bind("<Button-1>", lambda e: self.wait_for_key("mp"))

        ttk.Label(root, text="Buff鍵:").grid(row=2, column=2, sticky="e")
        self.insert_key_entries = []
        for i, key_var in enumerate(self.insert_keys):
            entry = ttk.Entry(root, textvariable=key_var, width=8)
            entry.grid(row=2+i, column=3)
            entry.bind("<Button-1>", lambda e, idx=i: self.wait_for_key("insert", idx))
            self.insert_key_entries.append(entry)
        self.add_buff_btn = ttk.Button(root, text="新增Buff鍵", command=self.add_buff_key)
        self.add_buff_btn.grid(row=2+len(self.insert_keys), column=3, sticky="ew")

        ttk.Label(root, text="Buff間隔(秒):").grid(row=3+len(self.insert_keys)-1, column=2, sticky="e")
        ttk.Entry(root, textvariable=self.buff_interval, width=8).grid(row=3+len(self.insert_keys)-1, column=3)

        self.start_btn = ttk.Button(root, text="開始", command=self.start)
        self.start_btn.grid(row=2, column=0, pady=5)
        self.pause_btn = ttk.Button(root, text="暫停", command=self.pause, state="disabled")
        self.pause_btn.grid(row=2, column=1, pady=5)
        ttk.Label(root, textvariable=self.status_var).grid(row=4, column=0, columnspan=4)

        # 綁定全域按鍵事件
        self.root.bind("<Key>", self.on_key_press)

    def add_buff_key(self):
        idx = len(self.insert_keys)
        new_var = tk.StringVar(value="")
        self.insert_keys.append(new_var)
        entry = ttk.Entry(self.root, textvariable=new_var, width=8)
        entry.grid(row=2+idx, column=3)
        entry.bind("<Button-1>", lambda e, idx=idx: self.wait_for_key("insert", idx))
        self.insert_key_entries.append(entry)
        # 重新放置Buff間隔欄位
        for widget in self.root.grid_slaves(row=3+idx-1, column=2):
            widget.grid_forget()
        for widget in self.root.grid_slaves(row=3+idx-1, column=3):
            widget.grid_forget()
        ttk.Label(self.root, text="Buff間隔(秒):").grid(row=3+idx, column=2, sticky="e")
        ttk.Entry(self.root, textvariable=self.buff_interval, width=8).grid(row=3+idx, column=3)

    def wait_for_key(self, key_type, idx=None):
        self._waiting_key = key_type
        self._waiting_key_idx = idx
        if key_type == "insert" and idx is not None:
            self.status_var.set(f"請按下要設定的Buff鍵{idx+1}（可連續按多個，用逗號分隔）...")
        else:
            self.status_var.set(f"請按下要設定的{key_type.upper()}鍵...")

    def on_key_press(self, event):
        if self._waiting_key:
            key_name = event.keysym.lower()
            if self._waiting_key == "hp":
                self.hp_key.set(key_name)
            elif self._waiting_key == "mp":
                self.mp_key.set(key_name)
            elif self._waiting_key == "insert" and self._waiting_key_idx is not None:
                # 若已有值則用逗號累加
                cur = self.insert_keys[self._waiting_key_idx].get()
                if cur:
                    if key_name not in [k.strip() for k in cur.split(",")]:
                        self.insert_keys[self._waiting_key_idx].set(cur + "," + key_name)
                else:
                    self.insert_keys[self._waiting_key_idx].set(key_name)
                self.status_var.set(f"Buff鍵{self._waiting_key_idx+1}已設定為: {self.insert_keys[self._waiting_key_idx].get()}")
            else:
                self.status_var.set(f"{self._waiting_key.upper()}鍵已設定為: {key_name}")
            # 若是insert，允許連續按多個，按下Enter才結束
            if not (self._waiting_key == "insert" and event.keysym.lower() != "return"):
                self._waiting_key = None
                self._waiting_key_idx = None

    def check_focus_and_toggle(self):
        try:
            active_win = gw.getActiveWindow()
            if active_win and "MapleStory Worlds" in active_win.title:
                if not self.running:
                    self.start()
            else:
                if self.running:
                    self.pause()
        except Exception as e:
            self.status_var.set(f"視窗偵測錯誤: {e}")
        self.root.after(self.focus_check_interval, self.check_focus_and_toggle)

    def start(self):
        if not self.running:
            self.running = True
            self.stop_event.clear()
            self.status_var.set("狀態: 執行中")
            self.start_btn.config(state="disabled")
            self.pause_btn.config(state="normal")
            self.thread = threading.Thread(target=self.worker, daemon=True)
            self.thread.start()
            self.auto_insert_thread = threading.Thread(
                target=auto_insert_loop,
                args=(self.get_all_buff_keys, self.stop_event,
                      lambda: self.running, lambda: self.buff_interval.get()),
                daemon=True
            )
            self.auto_insert_thread.start()

    def pause(self):
        self.running = False
        self.stop_event.set()
        self.status_var.set("狀態: 暫停")
        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled")

    def worker(self):
        window_title = "MapleStory Worlds"
        while self.running and not self.stop_event.is_set():
            bring_window_to_front(window_title)
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                self.status_var.set("找不到視窗")
                time.sleep(2)
                continue
            win = windows[0]
            win_left, win_top = win.left, win.top
            screenshot_img = pyautogui.screenshot()
            hp_region = (563, 1045, 670, 1065)
            mp_region = (808, 1045, 900, 1065)
            hp_img = get_fixed_area_screenshot(hp_region, win_left, win_top, screenshot_img=screenshot_img)
            hp_value, hp_max = ocr_number_from_image(hp_img)
            mp_img = get_fixed_area_screenshot(mp_region, win_left, win_top, screenshot_img=screenshot_img)
            mp_value, mp_max = ocr_number_from_image(mp_img)
            self.status_var.set(f"HP: {hp_value}/{hp_max}  MP: {mp_value}/{mp_max}")
            try:
                if hp_value and hp_max and self.hp_threshold.get() > 0 and int(hp_value) < self.hp_threshold.get():
                    pyautogui.press(self.hp_key.get())
            except Exception as e:
                self.status_var.set(f"HP 閾值判斷錯誤: {e}")
            try:
                if mp_value and mp_max and self.mp_threshold.get() > 0 and int(mp_value) < self.mp_threshold.get():
                    pyautogui.press(self.mp_key.get())
            except Exception as e:
                self.status_var.set(f"MP 閾值判斷錯誤: {e}")
            time.sleep(0.3)

    def get_all_buff_keys(self):
        # 將所有 insert_keys 的值用逗號分割並去除空白
        keys = []
        for var in self.insert_keys:
            for k in var.get().split(","):
                k = k.strip()
                if k:
                    keys.append(k)
        return keys


def main():
    root = tk.Tk()
    root.geometry("320x160")  # 設定視窗大小為320x160
    app = AutoPotionApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

# 打包成 exe 步驟（以 pyinstaller 為例）：

# 1. 安裝 pyinstaller
#    在命令提示字元(cmd)或PowerShell執行：
#    pip install pyinstaller

# 2. 進入 main.py 所在資料夾
#    cd c:\Users\Shooter\test\msw

# 3. 執行打包指令
#    pyinstaller --noconsole --onefile main.py

#    --noconsole 代表不顯示黑色命令視窗（GUI程式建議加上）
#    --onefile   代表產生單一 main.exe 檔案

# 4. 執行檔會在 dist\main.exe
#    請將 tesseract.exe 及相關圖片等資源一併放到同資料夾或設定好路徑

# 5. 若有額外資源（如 buff.png），可用 --add-data 參數：
#    pyinstaller --noconsole --onefile --add-data "buff.png;." main.py

# 6. 若遇到字型、OCR等問題，請確認 tesseract 路徑正確，或將 tesseract 安裝目錄加入 PATH。

# 參考官方文件：https://pyinstaller.org/en/stable/
