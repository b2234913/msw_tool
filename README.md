# MapleStory Worlds 自動補品/自動Buff GUI 工具

## 介紹

本工具為 MapleStory Worlds 遊戲設計的自動補品/自動Buff GUI 工具，支援自動偵測 HP/MP 數值並自動按下指定按鍵補品，並可定時自動按下多組 Buff 按鍵。
支援自訂補品鍵、Buff鍵、Buff間隔時間，並可自動偵測遊戲視窗是否在前景，自動啟動/暫停。

## 主要功能

- 自動偵測 MapleStory Worlds 視窗 HP/MP 數值，低於設定值自動補品
- 支援多組 Buff 按鍵，並可自訂間隔時間
- GUI 介面可即時調整所有參數
- 支援自訂補品鍵、Buff鍵（可多組、可複數鍵）
- 自動偵測 MapleStory Worlds 是否為前景視窗，非前景自動暫停
- 支援打包成單一 exe 檔案

## 執行需求

- Python 3.7+
- tesseract-ocr（需安裝並設定路徑）
- 主要依賴套件：`pyautogui`, `pygetwindow`, `opencv-python`, `pillow`, `pytesseract`, `tkinter`, `numpy`

安裝依賴：

```bash
pip install pyautogui pygetwindow opencv-python pillow pytesseract numpy
```

## 使用方式

1. **安裝 tesseract-ocr**
   下載安裝：<https://github.com/tesseract-ocr/tesseract>
   並確認 `main.py` 內的 `pytesseract.pytesseract.tesseract_cmd` 路徑正確。

2. **執行程式**

   ```bash
   python main.py
   ```

3. **設定說明**
   - HP/MP 閾值：低於此數值自動補品
   - HP/MP 補品鍵：自訂補品按鍵
   - Buff鍵：可設定多組，每組可輸入多個按鍵（用逗號分隔，如 `1,2`）
   - Buff間隔(秒)：每隔多少秒自動依序按下所有 Buff鍵
   - 點擊 Buff鍵欄位後，依序按下要設定的按鍵，按 Enter 結束

4. **自動啟停**
   - 只要 MapleStory Worlds 在最前景視窗，會自動開始
   - 切換到其他視窗會自動暫停

## 打包成 EXE

1. 安裝 pyinstaller

   ```bash
   pip install pyinstaller
   ```

2. 進入 main.py 所在資料夾

   ```bash
   cd c:\Users\<user>\test\msw
   ```

3. 執行打包指令

   ```bash
   pyinstaller --noconsole --onefile main.py
   ```

4. 執行檔會在 `dist\main.exe`，請將 tesseract.exe 及相關圖片等資源一併放到同資料夾或設定好路徑。

## 注意事項

- 若遇到 OCR 失敗，請確認 tesseract 路徑與遊戲解析度、數字區域座標正確。
- 若遊戲無法偵測到按鍵，請嘗試以系統管理員身份執行。
- 若有多組 Buff鍵，會依序每隔 1 秒按下一個（可自行調整 `time.sleep(1)`）。

---

如有問題請回報 issue 或自行修改 main.py。
