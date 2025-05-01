import logging
import asyncio
import os
import platform
import sys

# Thiết lập logging cơ bản
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Đang khởi động Bot điều khiển máy tính...")
    
    try:
        # Thử import các thư viện cần thiết để kiểm tra
        import telegram
        import pyautogui
        import nest_asyncio
        import numpy
        import cv2
        import dotenv
        from datetime import datetime
        from pynput.mouse import Controller
        
        # Kiểm tra thư viện tùy chọn
        try:
            from flask import Flask
            from pyngrok import ngrok
            has_flask_ngrok = True
            logger.info("Đã tìm thấy Flask và Ngrok - Hỗ trợ touchpad ảo")
        except ImportError:
            has_flask_ngrok = False
            logger.warning("Không tìm thấy Flask hoặc Ngrok - Tính năng touchpad ảo sẽ bị vô hiệu hóa")
            logger.info("Để sử dụng touchpad ảo, hãy cài đặt: pip install flask pyngrok")
        
        try:
            if platform.system() == "Windows":
                from pycaw.pycaw import AudioUtilities
                has_pycaw = True
                logger.info("Đã tìm thấy Pycaw - Hỗ trợ điều khiển âm lượng")
            else:
                has_pycaw = False
        except ImportError:
            has_pycaw = False
            if platform.system() == "Windows":
                logger.warning("Không tìm thấy Pycaw - Tính năng điều khiển âm lượng sẽ bị vô hiệu hóa")
                logger.info("Để sử dụng điều khiển âm lượng, hãy cài đặt: pip install pycaw")
        
        try:
            from playwright.async_api import async_playwright
            has_playwright = True
            logger.info("Đã tìm thấy Playwright - Hỗ trợ điều khiển trình duyệt")
        except ImportError:
            has_playwright = False
            logger.warning("Không tìm thấy Playwright - Tính năng điều khiển trình duyệt sẽ bị vô hiệu hóa")
            logger.info("Để sử dụng điều khiển trình duyệt, hãy cài đặt: pip install playwright")
            logger.info("Sau đó chạy: playwright install")
    
        # Kiểm tra file cấu hình ngôn ngữ
        config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
            logger.info(f"Đã tạo thư mục cấu hình tại: {config_dir}")
        
        # Tải language_config
        from language_config import load_language_config
        load_language_config()
        logger.info("Đã tải cấu hình ngôn ngữ")
        
        # Kiểm tra file .env
        if not os.path.exists('.env'):
            from dotenv import load_dotenv
            # Tạo file .env mẫu
            with open('.env', 'w') as f:
                f.write(f"TOKEN=REPLACE-YOUR-TOKEN\n")
                f.write(f"ALLOWED_USERS=REPLACE-YOUR-ID-CHAT\n")
                f.write(f"UPLOAD_FOLDER=\n")  # Để trống sẽ sử dụng thư mục mặc định
                f.write(f"NGROK_AUTH_TOKEN=\n")  # Không bắt buộc, chỉ cần nếu sử dụng touchpad ảo
            
            logger.info("Đã tạo file .env mẫu, vui lòng cập nhật thông tin trước khi chạy lại.")
            logger.info("Mở file .env và nhập TOKEN bot Telegram và ID người dùng được phép truy cập (cách nhau bởi dấu phẩy).")
            input("Nhấn Enter để thoát...")
            sys.exit(0)
            
        # Tải Bot_Control_Computer_Develop.py
        logger.info("Đang tải Bot điều khiển máy tính...")
        
        # Tải bot và chạy hàm main
        from Bot_Control_Computer import main
        asyncio.run(main())
        
    except ImportError as e:
        # Hiển thị thông báo lỗi và hướng dẫn cài đặt
        logger.error(f"Lỗi khi tải thư viện: {e}")
        logger.info("Vui lòng cài đặt đầy đủ các thư viện cần thiết bằng lệnh:")
        logger.info("pip install python-telegram-bot pyautogui opencv-python numpy nest-asyncio python-dotenv comtypes pynput")
        logger.info("Thư viện tùy chọn:")
        logger.info("pip install flask pyngrok")
        logger.info("pip install pycaw  # Chỉ cho Windows")
        logger.info("pip install playwright")
        logger.info("playwright install  # Sau khi cài đặt playwright")
        input("Nhấn Enter để thoát...")
    except Exception as e:
        # Bắt các lỗi khác
        logger.error(f"Lỗi không xác định: {e}")
        input("Nhấn Enter để thoát...")
