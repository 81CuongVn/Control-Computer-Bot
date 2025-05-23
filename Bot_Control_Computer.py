import os
import re
import time
import math
import asyncio
import pyautogui
import nest_asyncio
import numpy as np
import cv2
import comtypes
import threading
import platform
import logging
import json
from threading import Thread
from datetime import datetime
from pynput.mouse import Controller, Button
from playwright.async_api import async_playwright
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler, filters

# Import các module cho tính năng đa ngôn ngữ
from language_config import (
    load_language_config, 
    save_language_config, 
    get_user_language, 
    set_user_language,
    DEFAULT_LANGUAGE,
    USER_LANGUAGES
)
from translations import get_text, get_command_groups, get_commands, TRANSLATIONS
from language_functions import (
    create_confirmation_keyboard,
    create_stop_recording_keyboard,
    create_refresh_keyboard,
    create_browser_selection_keyboard,
    create_video_controls_keyboard,
    create_web_controls_keyboard,
    create_language_keyboard
)

# Thiết lập logging cơ bản
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Thêm thư viện dotenv để đọc file .env
from dotenv import load_dotenv

# Thêm các thư viện mới cho virtual touchpad
try:
    from flask import Flask, request, render_template, jsonify
    from pyngrok import ngrok, conf
    FLASK_NGROK_AVAILABLE = True
except ImportError:
    logger.warning("Flask hoặc pyngrok không có sẵn. Các tính năng touchpad ảo sẽ bị vô hiệu hóa.")
    FLASK_NGROK_AVAILABLE = False

# Import thư viện pycaw để điều khiển âm thanh - bọc trong try/except để xử lý lỗi
try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    PYCAW_AVAILABLE = True
except Exception as e:
    logger.warning(f"Lỗi khi import pycaw: {e}")
    PYCAW_AVAILABLE = False

# Áp dụng nest_asyncio để tránh xung đột event loop
nest_asyncio.apply()

# THIẾT LẬP CHUNG VÀ CẤU HÌNH

# Tải biến môi trường từ file .env
load_dotenv()

# Lấy Token Telegram Bot từ biến môi trường
BOT_TOKEN = os.getenv('TOKEN')

# Lấy danh sách người dùng được phép sử dụng bot
try:
    ALLOWED_USERS = [int(user_id) for user_id in os.getenv('ALLOWED_USERS', '').split(',') if user_id]
except (ValueError, TypeError) as e:
    logger.error(f"Lỗi khi phân tích danh sách ALLOWED_USERS: {e}")
    ALLOWED_USERS = []

# Đường dẫn lưu file tải về
if platform.system() == "Windows":
    DEFAULT_UPLOAD_FOLDER = "D:/"  #REPLACE YOUR UPLOAD FOLDER
else:  # Linux/Mac
    DEFAULT_UPLOAD_FOLDER = os.path.expanduser("~/Downloads/")

UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', DEFAULT_UPLOAD_FOLDER)

# Tạo thư mục nếu chưa tồn tại
try:
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
except PermissionError:
    logger.error(f"Không có quyền tạo thư mục tại {UPLOAD_FOLDER}")
    # Sử dụng thư mục hiện tại làm dự phòng
    UPLOAD_FOLDER = os.path.join(os.getcwd(), "downloads")
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    logger.info(f"Đã tạo thư mục dự phòng tại {UPLOAD_FOLDER}")

# Đường dẫn đến các trình duyệt - người dùng có thể tùy chỉnh
if platform.system() == "Windows":
    BROWSER_PATHS = {
        "chrome": "C:/Program Files/Google/Chrome/Application/chrome.exe",  #REPLACE YOUR BROWSER PATHS
        "brave": "C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe",
        "edge": "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
        "opera": "C:/Program Files/Opera/launcher.exe"
    }
    
    # Phát hiện tự động đường dẫn user data
    USER_DATA_DIRS = {
        "chrome": os.path.join(os.getenv('LOCALAPPDATA'), "Google/Chrome/User Data"),
        "brave": os.path.join(os.getenv('LOCALAPPDATA'), "BraveSoftware/Brave-Browser/User Data"),
        "edge": os.path.join(os.getenv('LOCALAPPDATA'), "Microsoft/Edge/User Data"),
        "opera": os.path.join(os.getenv('APPDATA'), "Opera Software/Opera Stable")
    }
else:
    # Đường dẫn trình duyệt cho Linux/Mac
    BROWSER_PATHS = {
        "chrome": "/usr/bin/google-chrome",
        "brave": "/usr/bin/brave-browser",
        "edge": "/usr/bin/microsoft-edge",
        "opera": "/usr/bin/opera"
    }
    
    # Đường dẫn user data cho Linux/Mac
    USER_DATA_DIRS = {
        "chrome": os.path.expanduser("~/.config/google-chrome"),
        "brave": os.path.expanduser("~/.config/BraveSoftware/Brave-Browser"),
        "edge": os.path.expanduser("~/.config/microsoft-edge"),
        "opera": os.path.expanduser("~/.config/opera")
    }

# Biến toàn cục cho Playwright
playwright = None
browser = None
page = None
current_browser_type = "brave"  # Trình duyệt mặc định

# Biến toàn cục cho quay video
is_recording = False
recording_thread = None

# Tạo đối tượng điều khiển chuột
try:
    mouse = Controller()
except Exception as e:
    logger.error(f"Không thể khởi tạo Controller chuột: {e}")
    mouse = None

# Port cho Flask server
FLASK_PORT = 5500

# Các biến cho Ngrok và quản lý touchpad
ngrok_tunnel = None
ngrok_auth_token = os.getenv('NGROK_AUTH_TOKEN')  # Lấy từ biến môi trường
flask_server_thread = None
current_touchpad_type = None  # 'mouse' hoặc 'volume' hoặc None
active_touchpad_chat_id = None  # Chat ID của người đang sử dụng touchpad
touchpad_active = False  # Trạng thái kích hoạt của touchpad

# KIỂM TRA QUYỀN NGƯỜI DÙNG

async def check_user_permission(update: Update) -> bool:
    """Kiểm tra xem người dùng có được phép sử dụng bot hay không"""
    user_id = update.effective_user.id
    
    # Nếu danh sách ALLOWED_USERS trống, cho phép tất cả người dùng
    if not ALLOWED_USERS:
        return True
    
    # Kiểm tra người dùng có trong danh sách được phép hay không
    if user_id in ALLOWED_USERS:
        return True
    
    # Thông báo cho người dùng không được phép, sử dụng bản dịch đa ngôn ngữ
    await update.message.reply_text(
        get_text("messages.permission_denied", user_id=user_id),
        parse_mode="HTML"
    )
    
    # Ghi log người dùng không được phép
    logger.warning(get_text("messages.no_permission_log", 
                          user_id=user_id, 
                          user_name=update.effective_user.first_name))
    
    return False

# CẤU HÌNH FLASK VÀ NGROK CHO TOUCHPAD ẢO

# Hàm quản lý touchpad hiện tại
async def stop_current_touchpad(update: Update = None, context: ContextTypes.DEFAULT_TYPE = None):
    """Dừng touchpad hiện tại đang chạy nếu có"""
    global current_touchpad_type, ngrok_tunnel, flask_server_thread, active_touchpad_chat_id, touchpad_active
    
    # Nếu không có touchpad nào đang chạy
    if current_touchpad_type is None or not touchpad_active:
        return True, "Không có touchpad nào đang chạy"
    
    try:
        # Lưu loại touchpad đang chạy để thông báo
        current_type = current_touchpad_type
        
        # Dừng Ngrok
        if ngrok_tunnel:
            try:
                stop_ngrok()
            except Exception as e:
                logger.error(f"Lỗi khi dừng Ngrok: {e}")
        
        # Ghi log và thông báo cho người dùng
        logger.info(f"Đã dừng touchpad {current_type}")
        
        # Nếu có update và context, gửi thông báo cho người dùng
        if update and context and active_touchpad_chat_id:
            # Nếu người gọi lệnh dừng khác với người đang sử dụng
            if update.effective_chat.id != active_touchpad_chat_id:
                # Thông báo cho người đang sử dụng touchpad
                try:
                    await context.bot.send_message(
                        chat_id=active_touchpad_chat_id,
                        text=f"<b>⚠️ Touchpad {current_type} của bạn đã bị dừng bởi người dùng khác.</b>",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"Lỗi khi gửi thông báo dừng touchpad: {e}")
        
        # Reset các biến toàn cục
        current_touchpad_type = None
        active_touchpad_chat_id = None
        touchpad_active = False
        
        return True, f"{current_type} touchpad"
    except Exception as e:
        logger.error(f"Lỗi khi dừng touchpad: {e}")
        return False, f"Lỗi khi dừng touchpad: {str(e)}"

# Kiểm tra khả năng sử dụng Flask và Ngrok
if FLASK_NGROK_AVAILABLE:
    # Khởi tạo Flask app
    app = Flask(__name__)

    # Tạo thư mục templates nếu chưa tồn tại
    TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    if not os.path.exists(TEMPLATES_DIR):
        os.makedirs(TEMPLATES_DIR)

    # Tạo file HTML cho touchpad
    TOUCHPAD_HTML_PATH = os.path.join(TEMPLATES_DIR, 'touchpad.html')
    with open(TOUCHPAD_HTML_PATH, 'w', encoding='utf-8') as f:
        f.write("""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Điều khiển Chuột</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Quicksand:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary-gradient: linear-gradient(135deg, #c2e9fb 0%, #a1c4fd 100%);
                --secondary-gradient: linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%);
                --accent-color: #6a11cb;
                --text-color: #4a4a6a;
                --light-text: #7a7a9a;
                --glass-bg: rgba(255, 255, 255, 0.25);
                --glass-border: rgba(255, 255, 255, 0.18);
                --shadow-sm: 0 4px 6px rgba(0, 0, 0, 0.05);
                --shadow-md: 0 8px 16px rgba(0, 0, 0, 0.08);
                --shadow-lg: 0 12px 24px rgba(0, 0, 0, 0.12);
                --radius-sm: 12px;
                --radius-md: 20px;
                --radius-lg: 30px;
                --transition-fast: 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94);
                --transition-medium: 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
                --transition-slow: 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94);
            }

            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Quicksand', sans-serif;
                background: #f8f9ff;
                color: var(--text-color);
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                overflow-x: hidden;
                touch-action: none;
                position: relative;
            }

            /* Background gradient animation */
            body::before, body::after {
                content: "";
                position: fixed;
                width: 300px;
                height: 300px;
                border-radius: 50%;
                background: var(--secondary-gradient);
                opacity: 0.5;
                filter: blur(80px);
                z-index: -1;
                animation: floatBubble 20s infinite alternate ease-in-out;
            }

            body::before {
                top: -100px;
                left: -100px;
                animation-delay: 0s;
            }

            body::after {
                bottom: -100px;
                right: -100px;
                background: var(--primary-gradient);
                animation-delay: -10s;
            }

            @keyframes floatBubble {
                0% {
                    transform: translate(0, 0) scale(1);
                }
                50% {
                    transform: translate(50px, 50px) scale(1.2);
                }
                100% {
                    transform: translate(10px, 30px) scale(1);
                }
            }

            .app-container {
                width: 100%;
                max-width: 500px;
                margin: 0 auto;
                padding: 20px;
                display: flex;
                flex-direction: column;
                height: 100vh;
                z-index: 1;
            }

            header {
                text-align: center;
                margin-bottom: 20px;
            }

            h1 {
                font-weight: 700;
                font-size: clamp(1.5rem, 5vw, 2rem);
                background: linear-gradient(to right, #6a11cb, #2575fc);
                -webkit-background-clip: text;
                background-clip: text;
                color: transparent;
                margin-bottom: 5px;
                letter-spacing: -0.5px;
            }

            .subtitle {
                font-weight: 400;
                font-size: clamp(0.9rem, 3vw, 1rem);
                color: var(--light-text);
            }

            #touchpad {
                flex: 1;
                background: var(--glass-bg);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                border-radius: var(--radius-lg);
                border: 1px solid var(--glass-border);
                box-shadow: var(--shadow-lg);
                position: relative;
                overflow: hidden;
                touch-action: none;
                margin-bottom: 20px;
                min-height: 250px;
                transition: box-shadow var(--transition-medium);
            }

            #touchpad:active {
                box-shadow: 0 4px 16px rgba(106, 17, 203, 0.2);
            }

            /* Ripple effect on touch */
            .ripple {
                position: absolute;
                border-radius: 50%;
                transform: scale(0);
                background: rgba(255, 255, 255, 0.7);
                pointer-events: none;
                animation: ripple 0.6s linear;
            }

            @keyframes ripple {
                to {
                    transform: scale(4);
                    opacity: 0;
                }
            }

            .cursor-indicator {
                position: absolute;
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background: linear-gradient(45deg, #6a11cb, #2575fc);
                box-shadow: 0 0 15px rgba(106, 17, 203, 0.5);
                transform: translate(-50%, -50%);
                pointer-events: none;
                opacity: 0;
                z-index: 10;
                transition: transform 0.1s ease, opacity 0.2s ease;
            }

            .cursor-indicator::after {
                content: '';
                position: absolute;
                width: 100%;
                height: 100%;
                border-radius: 50%;
                background: rgba(106, 17, 203, 0.3);
                z-index: -1;
                animation: pulse 1.5s infinite;
            }

            @keyframes pulse {
                0% {
                    transform: scale(1);
                    opacity: 1;
                }
                100% {
                    transform: scale(3);
                    opacity: 0;
                }
            }

            .controls-container {
                display: flex;
                flex-direction: column;
                gap: 15px;
            }

            .button-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
            }

            .action-button {
                background: var(--glass-bg);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                border: 1px solid var(--glass-border);
                border-radius: var(--radius-sm);
                padding: 15px 5px;
                font-family: 'Quicksand', sans-serif;
                font-weight: 600;
                font-size: 0.9rem;
                color: var(--text-color);
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all var(--transition-fast);
                box-shadow: var(--shadow-sm);
                position: relative;
                overflow: hidden;
            }

            .action-button:active {
                transform: translateY(2px);
                box-shadow: 0 2px 8px rgba(106, 17, 203, 0.15);
            }

            .action-button.active {
                background: linear-gradient(45deg, rgba(106, 17, 203, 0.15), rgba(37, 117, 252, 0.15));
                border-color: rgba(106, 17, 203, 0.2);
                color: var(--accent-color);
            }

            .action-button .icon {
                margin-right: 5px;
                font-size: 1.1rem;
            }

            .sensitivity-container {
                background: var(--glass-bg);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                border: 1px solid var(--glass-border);
                border-radius: var(--radius-sm);
                padding: 15px;
                box-shadow: var(--shadow-sm);
            }

            .sensitivity-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }

            .sensitivity-label {
                font-weight: 600;
                font-size: 0.9rem;
            }

            .sensitivity-value {
                font-weight: 700;
                font-size: 0.9rem;
                color: var(--accent-color);
                background: rgba(106, 17, 203, 0.1);
                padding: 3px 8px;
                border-radius: 12px;
            }

            .sensitivity-slider {
                width: 100%;
                -webkit-appearance: none;
                appearance: none;
                height: 6px;
                background: linear-gradient(to right, #c2e9fb, #a1c4fd);
                border-radius: 10px;
                outline: none;
                margin: 10px 0;
            }

            .sensitivity-slider::-webkit-slider-thumb {
                -webkit-appearance: none;
                appearance: none;
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background: linear-gradient(45deg, #6a11cb, #2575fc);
                cursor: pointer;
                box-shadow: 0 0 5px rgba(106, 17, 203, 0.5);
                border: 2px solid white;
                transition: all 0.2s ease;
            }

            .sensitivity-slider::-webkit-slider-thumb:active {
                transform: scale(1.2);
            }

            .status-container {
                text-align: center;
                margin-top: 10px;
                font-size: 0.85rem;
                font-weight: 500;
                color: var(--light-text);
                height: 20px;
                transition: all var(--transition-medium);
            }

            /* Animation for status update */
            .status-update {
                animation: statusPop 0.5s ease;
            }

            @keyframes statusPop {
                0% {
                    transform: scale(0.8);
                    opacity: 0;
                }
                50% {
                    transform: scale(1.1);
                }
                100% {
                    transform: scale(1);
                    opacity: 1;
                }
            }

            /* Touch guides */
            .touch-guides {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                opacity: 0.7;
                transition: opacity 0.3s ease;
                pointer-events: none;
            }

            .touch-guides svg {
                width: 80px;
                height: 80px;
                margin-bottom: 15px;
                fill: rgba(106, 17, 203, 0.2);
            }

            .touch-guide-text {
                font-size: 0.9rem;
                font-weight: 500;
                color: rgba(106, 17, 203, 0.5);
                text-align: center;
                max-width: 80%;
            }

            #touchpad:active .touch-guides {
                opacity: 0;
            }
        </style>
    </head>
    <body>
        <div class="app-container">
            <header>
                <h1>Điều khiển chuột</h1>
                <p class="subtitle">Control with elegance</p>
            </header>

            <div id="touchpad">
                <div class="cursor-indicator" id="cursor"></div>
                <div class="touch-guides">
                    <svg viewBox="0 0 24 24">
                        <path d="M9,11.24V7.5C9,6.12 10.12,5 11.5,5S14,6.12 14,7.5v3.74c1.21-0.81 2-2.18 2-3.74C16,5.01 13.99,3 11.5,3S7,5.01 7,7.5C7,9.06 7.79,10.43 9,11.24z M13,7.5V10.32l-1.5-0.79V7.5C11.5,6.67 12.17,6 13,6S14.5,6.67 14.5,7.5c0,0.88-0.33,1.69-0.89,2.3C13.58,9.8 13.5,9.66 13.5,9.5v-2H13z"/>
                        <path d="M11.5,13.5c-0.5,0-0.9,0.4-0.9,0.9v5.67l-1.07,1.77c-0.42,0.71,0.03,1.65,0.89,1.65h0.01c0.31,0 0.6-0.15 0.78-0.4l2.15-3.5C14.21,19 15,17.21 15,15.5c0-1.93-1.57-3.5-3.5-3.5V13.5z"/>
                    </svg>
                    <p class="touch-guide-text">Touch and drag to move cursor</p>
                </div>
            </div>

            <div class="controls-container">
                <div class="button-grid">
                    <button id="leftClick" class="action-button">
                        <span class="icon">👆</span> Left Click
                    </button>
                    <button id="rightClick" class="action-button">
                        <span class="icon">✌️</span> Right Click
                    </button>
                    <button id="doubleClick" class="action-button">
                        <span class="icon">👆👆</span> Double Click
                    </button>
                    <button id="scrollMode" class="action-button">
                        <span class="icon">↕️</span> Scroll Mode
                    </button>
                </div>

                <div class="sensitivity-container">
                    <div class="sensitivity-header">
                        <span class="sensitivity-label">Sensitivity</span>
                        <span class="sensitivity-value" id="sensitivityValue">1.5</span>
                    </div>
                    <input type="range" id="sensitivity" class="sensitivity-slider" min="0.5" max="3.0" step="0.1" value="1.5">
                </div>
            </div>

            <div class="status-container" id="status">Ready to control</div>
        </div>

        <script>
            const touchpad = document.getElementById('touchpad');
            const cursor = document.getElementById('cursor');
            const leftClickBtn = document.getElementById('leftClick');
            const rightClickBtn = document.getElementById('rightClick');
            const doubleClickBtn = document.getElementById('doubleClick');
            const scrollModeBtn = document.getElementById('scrollMode');
            const statusElem = document.getElementById('status');
            const sensitivitySlider = document.getElementById('sensitivity');
            const sensitivityValue = document.getElementById('sensitivityValue');
            
            let lastX = 0;
            let lastY = 0;
            let isTracking = false;
            let isScrollMode = false;
            let sensitivity = parseFloat(sensitivitySlider.value);
            
            // Update sensitivity value display
            sensitivitySlider.addEventListener('input', () => {
                sensitivity = parseFloat(sensitivitySlider.value);
                sensitivityValue.textContent = sensitivity.toFixed(1);
                updateStatus(`Sensitivity set to ${sensitivity.toFixed(1)}`);
            });
            
            // Toggle scroll mode
            scrollModeBtn.addEventListener('click', () => {
                isScrollMode = !isScrollMode;
                if (isScrollMode) {
                    scrollModeBtn.classList.add('active');
                    scrollModeBtn.innerHTML = `<span class="icon">↕️</span> Scroll: ON`;
                    updateStatus('Scroll Mode: Active');
                } else {
                    scrollModeBtn.classList.remove('active');
                    scrollModeBtn.innerHTML = `<span class="icon">↕️</span> Scroll Mode`;
                    updateStatus('Cursor Mode: Active');
                }
                // Add button press effect
                addButtonPressEffect(scrollModeBtn);
            });
            
            // Create ripple effect
            function createRipple(event, element) {
                const ripple = document.createElement('span');
                const rect = element.getBoundingClientRect();
                
                const size = Math.max(rect.width, rect.height);
                const x = event.clientX - rect.left - size / 2;
                const y = event.clientY - rect.top - size / 2;
                
                ripple.style.width = ripple.style.height = `${size}px`;
                ripple.style.left = `${x}px`;
                ripple.style.top = `${y}px`;
                ripple.classList.add('ripple');
                
                element.appendChild(ripple);
                
                setTimeout(() => {
                    ripple.remove();
                }, 600);
            }
            
            // Create touch ripple effect
            function createTouchRipple(event, element) {
                const touch = event.touches[0];
                const ripple = document.createElement('span');
                const rect = element.getBoundingClientRect();
                
                const size = Math.max(rect.width, rect.height);
                const x = touch.clientX - rect.left - size / 2;
                const y = touch.clientY - rect.top - size / 2;
                
                ripple.style.width = ripple.style.height = `${size}px`;
                ripple.style.left = `${x}px`;
                ripple.style.top = `${y}px`;
                ripple.classList.add('ripple');
                
                element.appendChild(ripple);
                
                setTimeout(() => {
                    ripple.remove();
                }, 600);
            }
            
            // Add button press effect
            function addButtonPressEffect(button) {
                button.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    button.style.transform = '';
                }, 150);
            }
            
            // Update status with animation
            function updateStatus(message) {
                statusElem.textContent = '';
                setTimeout(() => {
                    statusElem.textContent = message;
                    statusElem.classList.add('status-update');
                    setTimeout(() => {
                        statusElem.classList.remove('status-update');
                    }, 500);
                }, 10);
            }
            
            // Handle touch events for mobile
            touchpad.addEventListener('touchstart', (e) => {
                e.preventDefault();
                isTracking = true;
                lastX = e.touches[0].clientX;
                lastY = e.touches[0].clientY;
                
                // Show cursor indicator with animation
                cursor.style.opacity = '1';
                cursor.style.left = `${lastX}px`;
                cursor.style.top = `${lastY}px`;
                
                // Create ripple effect
                createTouchRipple(e, touchpad);
            });
            
            touchpad.addEventListener('touchmove', (e) => {
                if (!isTracking) return;
                e.preventDefault();
                
                const touchX = e.touches[0].clientX;
                const touchY = e.touches[0].clientY;
                
                // Update cursor indicator position
                cursor.style.left = `${touchX}px`;
                cursor.style.top = `${touchY}px`;
                
                const dx = (touchX - lastX) * sensitivity;
                const dy = (touchY - lastY) * sensitivity;
                
                if (isScrollMode) {
                    // In scroll mode, only use vertical movement for scrolling
                    sendScroll(dy);
                    updateStatus(`Scrolling: ${dy > 0 ? 'Down' : 'Up'}`);
                } else {
                    // Normal mouse movement
                    sendMovement(dx, dy);
                    updateStatus('Moving cursor');
                }
                
                lastX = touchX;
                lastY = touchY;
            });
            
            touchpad.addEventListener('touchend', () => {
                isTracking = false;
                // Hide cursor with fade out
                cursor.style.opacity = '0';
                updateStatus(isScrollMode ? 'Scroll Mode: Ready' : 'Cursor Mode: Ready');
            });
            
            // Handle mouse events for desktop
            touchpad.addEventListener('mousedown', (e) => {
                isTracking = true;
                lastX = e.clientX;
                lastY = e.clientY;
                
                // Show cursor indicator
                cursor.style.opacity = '1';
                cursor.style.left = `${lastX}px`;
                cursor.style.top = `${lastY}px`;
                
                // Create ripple effect
                createRipple(e, touchpad);
            });
            
            touchpad.addEventListener('mousemove', (e) => {
                if (!isTracking) return;
                
                // Update cursor indicator position
                cursor.style.left = `${e.clientX}px`;
                cursor.style.top = `${e.clientY}px`;
                
                const dx = (e.clientX - lastX) * sensitivity;
                const dy = (e.clientY - lastY) * sensitivity;
                
                if (isScrollMode) {
                    // In scroll mode, only use vertical movement for scrolling
                    sendScroll(dy);
                    updateStatus(`Scrolling: ${dy > 0 ? 'Down' : 'Up'}`);
                } else {
                    // Normal mouse movement
                    sendMovement(dx, dy);
                    updateStatus('Moving cursor');
                }
                
                lastX = e.clientX;
                lastY = e.clientY;
            });
            
            touchpad.addEventListener('mouseup', () => {
                isTracking = false;
                // Hide cursor with fade out
                cursor.style.opacity = '0';
                updateStatus(isScrollMode ? 'Scroll Mode: Ready' : 'Cursor Mode: Ready');
            });
            
            // Button clicks with effects
            leftClickBtn.addEventListener('click', () => {
                sendClick('left');
                updateStatus('Left click sent');
                addButtonPressEffect(leftClickBtn);
            });
            
            rightClickBtn.addEventListener('click', () => {
                sendClick('right');
                updateStatus('Right click sent');
                addButtonPressEffect(rightClickBtn);
            });
            
            doubleClickBtn.addEventListener('click', () => {
                sendDoubleClick();
                updateStatus('Double click sent');
                addButtonPressEffect(doubleClickBtn);
            });
            
            // Send movement to server
            function sendMovement(dx, dy) {
                fetch('/move', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ dx, dy })
                }).catch(error => {
                    console.error('Error sending movement:', error);
                    updateStatus('Connection error');
                });
            }
            
            // Send scroll to server
            function sendScroll(amount) {
                fetch('/scroll', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ amount })
                }).catch(error => {
                    console.error('Error sending scroll:', error);
                    updateStatus('Connection error');
                });
            }
            
            // Send click to server
            function sendClick(button) {
                fetch('/click', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ button })
                }).catch(error => {
                    console.error('Error sending click:', error);
                    updateStatus('Connection error');
                });
            }
            
            // Send double click to server
            function sendDoubleClick() {
                fetch('/doubleclick', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ button: 'left' })
                }).catch(error => {
                    console.error('Error sending double click:', error);
                    updateStatus('Connection error');
                });
            }
            
            // Initialize
            window.addEventListener('load', () => {
                updateStatus('Ready to control');
            });
        </script>
    </body>
    </html>""")

    # Route chính cho touchpad
    @app.route('/')
    def touchpad():
        return render_template('touchpad.html')

    # API endpoint để di chuyển chuột
    @app.route('/move', methods=['POST'])
    def move_mouse():
        if not mouse:
            return jsonify({"status": "error", "message": "Mouse controller not available"}), 500
            
        data = request.json
        dx = data.get('dx', 0)
        dy = data.get('dy', 0)
        
        try:
            # Chuyển đổi sang int để tránh các giá trị phẩy động quá nhỏ
            dx = int(dx)
            dy = int(dy)
            
            # Di chuyển chuột
            mouse.move(dx, dy)
            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Lỗi khi di chuyển chuột: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    # API endpoint để scroll
    @app.route('/scroll', methods=['POST'])
    def scroll_mouse():
        if not mouse:
            return jsonify({"status": "error", "message": "Mouse controller not available"}), 500
            
        data = request.json
        amount = data.get('amount', 0)
        
        try:
            # Chia cho 10 để làm giảm tốc độ cuộn
            scroll_amount = int(amount) / 10
            
            # Scroll chuột (giá trị dương cuộn xuống, âm cuộn lên)
            mouse.scroll(0, scroll_amount)
            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Lỗi khi scroll chuột: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    # API endpoint để click chuột
    @app.route('/click', methods=['POST'])
    def click_mouse():
        if not mouse:
            return jsonify({"status": "error", "message": "Mouse controller not available"}), 500
            
        data = request.json
        button = data.get('button', 'left')
        
        try:
            if button == 'left':
                mouse.click(Button.left)
            elif button == 'right':
                mouse.click(Button.right)
            
            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Lỗi khi click chuột: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    # API endpoint để double click
    @app.route('/doubleclick', methods=['POST'])
    def doubleclick_mouse():
        if not mouse:
            return jsonify({"status": "error", "message": "Mouse controller not available"}), 500
            
        try:
            mouse.click(Button.left, 2)  # Click 2 lần
            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Lỗi khi double click chuột: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
        
    # Khởi tạo Flask server
    def start_flask_server():
        """Khởi động Flask server với xử lý COM riêng cho từng thread"""
        try:
            # Đảm bảo thread Flask cũng khởi tạo COM
            if platform.system() == "Windows":  # COM chỉ có trên Windows
                comtypes.CoInitialize()
            # Chạy Flask
            app.run(host='0.0.0.0', port=FLASK_PORT, debug=False, threaded=True)
        except Exception as e:
            logger.error(f"Lỗi khi khởi động Flask server: {e}")
        finally:
            # Giải phóng COM khi thread kết thúc
            if platform.system() == "Windows":  # COM chỉ có trên Windows
                try:
                    comtypes.CoUninitialize()
                except:
                    pass

    # Hàm khởi động Ngrok và lấy URL công khai
    def start_ngrok():
        global ngrok_tunnel, ngrok_auth_token
        
        try:
            # Cấu hình Ngrok
            if ngrok_auth_token:
                conf.get_default().auth_token = ngrok_auth_token
            
            # Dừng bất kỳ tunnel nào đang chạy trước khi tạo mới
            stop_ngrok()
            
            # Kết nối Ngrok đến port của Flask
            ngrok_tunnel = ngrok.connect(FLASK_PORT)
            logger.info(f"Ngrok URL: {ngrok_tunnel.public_url}")
            return ngrok_tunnel.public_url
        except Exception as e:
            logger.error(f"Lỗi khi khởi động Ngrok: {e}")
            return None

    # Hàm dừng Ngrok
    def stop_ngrok():
        global ngrok_tunnel
        try:
            # Kiểm tra xem có tunnel nào đang mở không
            tunnels = ngrok.get_tunnels()
            if tunnels:
                for tunnel in tunnels:
                    try:
                        ngrok.disconnect(tunnel.public_url)
                        logger.info(f"Đã đóng Ngrok tunnel: {tunnel.public_url}")
                    except Exception as e:
                        logger.error(f"Lỗi khi đóng Ngrok tunnel {tunnel.public_url}: {e}")
            
            if ngrok_tunnel:
                try:
                    ngrok.disconnect(ngrok_tunnel.public_url)
                    logger.info(f"Đã đóng Ngrok tunnel chính: {ngrok_tunnel.public_url}")
                except Exception as e:
                    logger.error(f"Lỗi khi đóng Ngrok tunnel chính: {e}")
                ngrok_tunnel = None
        except Exception as e:
            logger.error(f"Lỗi khi dừng Ngrok: {e}")

# Tạo template HTML cho touchpad âm lượng
if FLASK_NGROK_AVAILABLE:
    VOLUME_TOUCHPAD_HTML_PATH = os.path.join(TEMPLATES_DIR, 'volume_touchpad.html')
    with open(VOLUME_TOUCHPAD_HTML_PATH, 'w', encoding='utf-8') as f:
        f.write("""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Điều Khiển Âm Lượng</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Quicksand:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary-gradient: linear-gradient(135deg, #89f7fe 0%, #66a6ff 100%);
                --secondary-gradient: linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%);
                --accent-color: #7366ff;
                --text-color: #4a4a6a;
                --light-text: #7a7a9a;
                --glass-bg: rgba(255, 255, 255, 0.25);
                --glass-border: rgba(255, 255, 255, 0.18);
                --shadow-sm: 0 4px 6px rgba(0, 0, 0, 0.05);
                --shadow-md: 0 8px 16px rgba(0, 0, 0, 0.08);
                --shadow-lg: 0 12px 24px rgba(0, 0, 0, 0.12);
                --shadow-inner: inset 0 2px 4px rgba(0, 0, 0, 0.05);
                --radius-sm: 12px;
                --radius-md: 20px;
                --radius-lg: 30px;
                --radius-full: 9999px;
                --transition-fast: 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94);
                --transition-medium: 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
                --transition-slow: 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94);
                --transition-bounce: 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
            }

            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Quicksand', sans-serif;
                background: #f8f9ff;
                color: var(--text-color);
                min-height: 100vh;
                touch-action: none;
                position: relative;
                overflow-x: hidden;
            }

            /* Background gradient animation */
            body::before, body::after {
                content: "";
                position: fixed;
                width: 300px;
                height: 300px;
                border-radius: 50%;
                background: var(--secondary-gradient);
                opacity: 0.5;
                filter: blur(80px);
                z-index: -1;
                animation: floatBubble 15s infinite alternate ease-in-out;
            }

            body::before {
                top: -100px;
                right: -50px;
                animation-delay: 0s;
            }

            body::after {
                bottom: -100px;
                left: -50px;
                background: var(--primary-gradient);
                animation-delay: -7s;
            }

            @keyframes floatBubble {
                0% {
                    transform: translate(0, 0) scale(1);
                }
                50% {
                    transform: translate(30px, 30px) scale(1.1);
                }
                100% {
                    transform: translate(10px, 20px) scale(1);
                }
            }

            .app-container {
                width: 100%;
                max-width: 500px;
                margin: 0 auto;
                padding: 20px;
                display: flex;
                flex-direction: column;
                height: 100vh;
                z-index: 1;
            }

            header {
                text-align: center;
                margin-bottom: 20px;
                animation: fadeIn 1s ease;
            }

            @keyframes fadeIn {
                from {
                    opacity: 0;
                    transform: translateY(-10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            h1 {
                font-weight: 700;
                font-size: clamp(1.5rem, 6vw, 2.2rem);
                background: linear-gradient(to right, #7366ff, #a47cff);
                -webkit-background-clip: text;
                background-clip: text;
                color: transparent;
                margin-bottom: 5px;
                letter-spacing: -0.5px;
            }

            /* Volume display section */
            .volume-display-container {
                text-align: center;
                margin-bottom: 30px;
                position: relative;
                animation: fadeIn 1s ease 0.2s both;
            }

            .volume-percentage {
                font-size: clamp(3rem, 15vw, 5rem);
                font-weight: 700;
                background: linear-gradient(45deg, #7366ff, #a47cff);
                -webkit-background-clip: text;
                background-clip: text;
                color: transparent;
                line-height: 1;
                transition: all var(--transition-bounce);
                position: relative;
                margin-bottom: 10px;
            }

            .volume-percentage.changing {
                transform: scale(1.1);
            }

            /* Volume circular indicator */
            .volume-ring-container {
                position: relative;
                width: 200px;
                height: 200px;
                margin: 0 auto 20px;
                animation: fadeIn 1s ease 0.4s both;
            }

            .volume-ring-background {
                width: 100%;
                height: 100%;
                border-radius: 50%;
                background: var(--glass-bg);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                box-shadow: var(--shadow-md), var(--shadow-inner);
                border: 1px solid var(--glass-border);
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
                overflow: hidden;
            }

            .volume-ring-progress {
                position: absolute;
                width: 100%;
                height: 100%;
                border-radius: 50%;
                clip: rect(0, 100px, 200px, 0);
                background: conic-gradient(
                    from 0deg,
                    rgba(115, 102, 255, 0.2) 0%,
                    rgba(115, 102, 255, 0.4) 50%,
                    rgba(115, 102, 255, 0.8) 100%
                );
                transition: transform var(--transition-medium);
            }

            .volume-label {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 3rem;
                font-weight: 700;
                background: linear-gradient(45deg, #7366ff, #a47cff);
                -webkit-background-clip: text;
                background-clip: text;
                color: transparent;
                transition: all var(--transition-bounce);
                z-index: 10;
            }

            .volume-label.changing {
                transform: translate(-50%, -50%) scale(1.1);
            }

            /* Volume sound waves animation */
            .volume-waves {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 180px;
                height: 180px;
                border-radius: 50%;
                z-index: 1;
                opacity: 0.7;
            }

            .wave {
                position: absolute;
                border: 2px solid rgba(115, 102, 255, 0.3);
                border-radius: 50%;
                width: 100%;
                height: 100%;
                opacity: 0;
                animation: wave 3s infinite ease-out;
            }

            .wave:nth-child(2) {
                animation-delay: 0.5s;
            }

            .wave:nth-child(3) {
                animation-delay: 1s;
            }

            @keyframes wave {
                0% {
                    transform: scale(0.5);
                    opacity: 0.8;
                }
                100% {
                    transform: scale(1);
                    opacity: 0;
                }
            }

            /* Volume slider area */
            .volume-touchpad-container {
                flex: 1;
                background: var(--glass-bg);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                border-radius: var(--radius-md);
                border: 1px solid var(--glass-border);
                box-shadow: var(--shadow-lg);
                position: relative;
                overflow: hidden;
                margin-bottom: 20px;
                min-height: 120px;
                animation: fadeIn 1s ease 0.6s both;
            }

            .volume-slider {
                position: absolute;
                width: 90%;
                height: 60px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 30px;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                box-shadow: var(--shadow-inner);
            }

            .volume-handle {
                position: absolute;
                width: 60px;
                height: 60px;
                background: linear-gradient(45deg, #7366ff, #a47cff);
                border-radius: 50%;
                top: 0;
                left: 50%;
                transform: translateX(-50%);
                box-shadow: 0 4px 10px rgba(115, 102, 255, 0.5);
                cursor: grab;
                transition: box-shadow 0.2s, transform 0.2s;
                border: 3px solid rgba(255, 255, 255, 0.8);
                z-index: 10;
            }

            .volume-handle:active {
                cursor: grabbing;
                transform: translateX(-50%) scale(1.1);
                box-shadow: 0 6px 15px rgba(115, 102, 255, 0.7);
            }

            .volume-handle::after {
                content: '';
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 30%;
                height: 30%;
                background: rgba(255, 255, 255, 0.9);
                border-radius: 50%;
            }

            .volume-track {
                position: absolute;
                height: 100%;
                left: 0;
                top: 0;
                width: 50%;
                background: linear-gradient(to right, rgba(115, 102, 255, 0.2), rgba(115, 102, 255, 0.5));
                border-radius: 30px 0 0 30px;
                transition: width var(--transition-medium);
            }

            .slider-markers {
                position: absolute;
                width: 90%;
                height: 10px;
                top: calc(50% + 40px);
                left: 50%;
                transform: translateX(-50%);
                display: flex;
                justify-content: space-between;
            }

            .slider-marker {
                width: 2px;
                height: 10px;
                background: rgba(115, 102, 255, 0.2);
                border-radius: 1px;
            }

            .slider-marker.active {
                background: rgba(115, 102, 255, 0.8);
                height: 15px;
                transform: translateY(-2px);
            }

            .touchpad-instruction {
                position: absolute;
                bottom: 5px;
                left: 0;
                width: 100%;
                text-align: center;
                color: var(--light-text);
                font-size: 0.85rem;
                font-weight: 500;
                opacity: 0.7;
                pointer-events: none;
            }

            /* Button controls */
            .button-row {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 15px;
                margin-bottom: 15px;
                animation: fadeIn 1s ease 0.8s both;
            }

            .volume-button {
                background: var(--glass-bg);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                border: 1px solid var(--glass-border);
                border-radius: var(--radius-sm);
                padding: 15px 5px;
                font-family: 'Quicksand', sans-serif;
                font-weight: 600;
                font-size: 0.9rem;
                color: var(--text-color);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all var(--transition-fast);
                box-shadow: var(--shadow-sm);
            }

            .volume-button .icon {
                font-size: 1.5rem;
                margin-bottom: 5px;
            }

            .volume-button:active {
                transform: scale(0.95);
                box-shadow: 0 2px 8px rgba(115, 102, 255, 0.15);
            }

            /* Status message */
            .status {
                text-align: center;
                color: var(--light-text);
                font-size: 0.85rem;
                font-weight: 500;
                height: 20px;
                margin-top: 5px;
                animation: fadeIn 1s ease 1s both;
            }

            /* Ripple effect */
            .ripple {
                position: absolute;
                border-radius: 50%;
                transform: scale(0);
                background: rgba(255, 255, 255, 0.7);
                pointer-events: none;
                animation: ripple 0.6s linear;
            }

            @keyframes ripple {
                to {
                    transform: scale(4);
                    opacity: 0;
                }
            }
        </style>
    </head>
    <body>
        <div class="app-container">
            <header>
                <h1>Điều Khiển Âm Lượng</h1>
            </header>

            <div class="volume-ring-container">
                <div class="volume-ring-background">
                    <div class="volume-label" id="volumeLabel">50</div>
                    <div class="volume-ring-progress" id="volumeRing" style="transform: rotate(180deg);"></div>
                    <div class="volume-waves">
                        <div class="wave"></div>
                        <div class="wave"></div>
                        <div class="wave"></div>
                    </div>
                </div>
            </div>

            <div class="volume-touchpad-container" id="volumeTouchpad">
                <div class="volume-slider">
                    <div class="volume-track" id="volumeTrack"></div>
                    <div class="volume-handle" id="volumeHandle"></div>
                </div>
                
                <div class="slider-markers" id="sliderMarkers">
                    <!-- Markers will be added by JavaScript -->
                </div>
                
                <div class="touchpad-instruction">← Kéo để điều chỉnh âm lượng →</div>
            </div>

            <div class="button-row">
                <button id="muteButton" class="volume-button">
                    <span class="icon">🔇</span> 
                    <span>Tắt tiếng</span>
                </button>
                <button id="vol50Button" class="volume-button">
                    <span class="icon">🔉</span>
                    <span>50%</span>
                </button>
                <button id="vol100Button" class="volume-button">
                    <span class="icon">🔊</span>
                    <span>100%</span>
                </button>
            </div>

            <div class="status" id="status">Chạm và kéo để điều chỉnh âm lượng</div>
        </div>

        <script>
            const touchpad = document.getElementById('volumeTouchpad');
            const handle = document.getElementById('volumeHandle');
            const volumeTrack = document.getElementById('volumeTrack');
            const volumeLabel = document.getElementById('volumeLabel');
            const volumeRing = document.getElementById('volumeRing');
            const sliderMarkers = document.getElementById('sliderMarkers');
            const muteButton = document.getElementById('muteButton');
            const vol50Button = document.getElementById('vol50Button');
            const vol100Button = document.getElementById('vol100Button');
            const statusElem = document.getElementById('status');
            
            let isDragging = false;
            let currentVolume = 50; // Default volume percentage
            let sliderWidth;
            let markerElements = [];
            let startX;
            let handleStartPosition;
            
            // Create markers
            function createMarkers() {
                sliderMarkers.innerHTML = '';
                markerElements = [];
                
                // Create 11 markers (0%, 10%, 20%, ..., 100%)
                for (let i = 0; i <= 10; i++) {
                    const marker = document.createElement('div');
                    marker.classList.add('slider-marker');
                    if (i * 10 <= currentVolume) {
                        marker.classList.add('active');
                    }
                    sliderMarkers.appendChild(marker);
                    markerElements.push(marker);
                }
            }
            
            // Initialize handle position and UI
            function initHandle() {
                const slider = document.querySelector('.volume-slider');
                sliderWidth = slider.offsetWidth;
                const handleWidth = handle.offsetWidth;
                
                // Position handle based on current volume
                const handlePosition = ((currentVolume / 100) * (sliderWidth - handleWidth)) + (handleWidth / 2);
                handle.style.left = `${handlePosition}px`;
                
                // Update volume track
                volumeTrack.style.width = `${currentVolume}%`;
                
                // Update ring rotation (180deg = 0%, 540deg = 100%)
                const rotation = 180 + ((currentVolume / 100) * 360);
                volumeRing.style.transform = `rotate(${rotation}deg)`;
                
                // Update markers
                updateMarkers();
            }
            
            // Update active markers based on current volume
            function updateMarkers() {
                markerElements.forEach((marker, index) => {
                    if (index * 10 <= currentVolume) {
                        marker.classList.add('active');
                    } else {
                        marker.classList.remove('active');
                    }
                });
            }
            
            // Set volume and update UI
            function setVolume(volumePercent, animate = true) {
                // Clamp volume between 0 and 100
                currentVolume = Math.max(0, Math.min(100, Math.round(volumePercent)));
                
                // Update UI elements
                volumeLabel.textContent = currentVolume;
                volumeTrack.style.width = `${currentVolume}%`;
                
                // Animate volume change
                if (animate) {
                    volumeLabel.classList.add('changing');
                    setTimeout(() => {
                        volumeLabel.classList.remove('changing');
                    }, 300);
                }
                
                // Update ring rotation (180deg = 0%, 540deg = 100%)
                const rotation = 180 + ((currentVolume / 100) * 360);
                volumeRing.style.transform = `rotate(${rotation}deg)`;
                
                // Update markers
                updateMarkers();
                
                // Send volume to server
                sendVolumeChange(currentVolume);
                
                // Update status message
                statusElem.textContent = `Âm lượng: ${currentVolume}%`;
                
                // Adjust wave animation speed based on volume
                const waves = document.querySelectorAll('.wave');
                const animationDuration = currentVolume > 0 ? Math.max(1, 4 - (currentVolume / 33)) : 0;
                waves.forEach(wave => {
                    if (currentVolume > 0) {
                        wave.style.animationDuration = `${animationDuration}s`;
                        wave.style.opacity = currentVolume / 200;
                    } else {
                        wave.style.opacity = '0';
                    }
                });
            }
            
            // Create ripple effect
            function createRipple(event, element) {
                const ripple = document.createElement('span');
                const rect = element.getBoundingClientRect();
                
                const size = Math.max(rect.width, rect.height);
                const x = event.clientX - rect.left - size / 2;
                const y = event.clientY - rect.top - size / 2;
                
                ripple.style.width = ripple.style.height = `${size}px`;
                ripple.style.left = `${x}px`;
                ripple.style.top = `${y}px`;
                ripple.classList.add('ripple');
                
                element.appendChild(ripple);
                
                setTimeout(() => {
                    ripple.remove();
                }, 600);
            }
            
            // Create touch ripple effect
            function createTouchRipple(event, element) {
                const touch = event.touches[0];
                const ripple = document.createElement('span');
                const rect = element.getBoundingClientRect();
                
                const size = Math.max(rect.width, rect.height);
                const x = touch.clientX - rect.left - size / 2;
                const y = touch.clientY - rect.top - size / 2;
                
                ripple.style.width = ripple.style.height = `${size}px`;
                ripple.style.left = `${x}px`;
                ripple.style.top = `${y}px`;
                ripple.classList.add('ripple');
                
                element.appendChild(ripple);
                
                setTimeout(() => {
                    ripple.remove();
                }, 600);
            }
            
            // TouchStart handler
            touchpad.addEventListener('touchstart', (e) => {
                if (e.target === handle || e.target.closest('.volume-slider')) {
                    e.preventDefault();
                    createTouchRipple(e, touchpad);
                    startDrag(e.touches[0].clientX);
                }
            });
            
            // TouchMove handler
            touchpad.addEventListener('touchmove', (e) => {
                if (isDragging) {
                    e.preventDefault();
                    updateDrag(e.touches[0].clientX);
                }
            });
            
            // TouchEnd handler
            touchpad.addEventListener('touchend', () => {
                endDrag();
            });
            
            // MouseDown handler (for desktop testing)
            touchpad.addEventListener('mousedown', (e) => {
                if (e.target === handle || e.target.closest('.volume-slider')) {
                    e.preventDefault();
                    createRipple(e, touchpad);
                    startDrag(e.clientX);
                }
            });
            
            // MouseMove handler
            document.addEventListener('mousemove', (e) => {
                if (isDragging) {
                    e.preventDefault();
                    updateDrag(e.clientX);
                }
            });
            
            // MouseUp handler
            document.addEventListener('mouseup', () => {
                endDrag();
            });
            
            // Start dragging
            function startDrag(clientX) {
                isDragging = true;
                startX = clientX;
                handleStartPosition = handle.offsetLeft;
                handle.style.boxShadow = '0 6px 15px rgba(115, 102, 255, 0.7)';
                handle.style.transform = 'translateX(-50%) scale(1.1)';
            }
            
            // Update while dragging
            function updateDrag(clientX) {
                if (!isDragging) return;
                
                const deltaX = clientX - startX;
                const slider = document.querySelector('.volume-slider');
                const sliderRect = slider.getBoundingClientRect();
                const sliderWidth = sliderRect.width;
                const handleWidth = handle.offsetWidth;
                
                // Calculate new handle position
                let newPosition = handleStartPosition + deltaX;
                const minPosition = handleWidth / 2;
                const maxPosition = sliderWidth - (handleWidth / 2);
                
                // Constrain handle within bounds
                newPosition = Math.max(minPosition, Math.min(maxPosition, newPosition));
                
                // Update handle position
                handle.style.left = `${newPosition}px`;
                
                // Calculate and set volume
                const volumePercent = ((newPosition - minPosition) / (maxPosition - minPosition)) * 100;
                setVolume(volumePercent);
            }
            
            // End dragging
            function endDrag() {
                if (isDragging) {
                    isDragging = false;
                    handle.style.boxShadow = '0 4px 10px rgba(115, 102, 255, 0.5)';
                    handle.style.transform = 'translateX(-50%)';
                }
            }
            
            // Add button press effect
            function addButtonPressEffect(button) {
                button.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    button.style.transform = '';
                }, 150);
            }
            
            // Button click handlers
            muteButton.addEventListener('click', (e) => {
                createRipple(e, muteButton);
                setVolume(0);
                updateHandlePosition(0);
                addButtonPressEffect(muteButton);
            });
            
            vol50Button.addEventListener('click', (e) => {
                createRipple(e, vol50Button);
                setVolume(50);
                updateHandlePosition(50);
                addButtonPressEffect(vol50Button);
            });
            
            vol100Button.addEventListener('click', (e) => {
                createRipple(e, vol100Button);
                setVolume(100);
                updateHandlePosition(100);
                addButtonPressEffect(vol100Button);
            });
            
            // Update handle position based on volume
            function updateHandlePosition(volumePercent) {
                const slider = document.querySelector('.volume-slider');
                const sliderWidth = slider.offsetWidth;
                const handleWidth = handle.offsetWidth;
                
                const minPosition = handleWidth / 2;
                const maxPosition = sliderWidth - (handleWidth / 2);
                const newPosition = minPosition + ((volumePercent / 100) * (maxPosition - minPosition));
                
                handle.style.left = `${newPosition}px`;
            }
            
            // Send volume change to server
            function sendVolumeChange(volumePercent) {
                fetch('/setvolume', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ volume: volumePercent })
                }).catch(error => {
                    console.error('Error sending volume change:', error);
                    statusElem.textContent = 'Lỗi kết nối';
                });
            }
            
            // Get current volume on page load
            function getCurrentVolume() {
                fetch('/getvolume')
                    .then(response => response.json())
                    .then(data => {
                        setVolume(data.volume, false);
                        initHandle();
                    })
                    .catch(error => {
                        console.error('Error getting current volume:', error);
                        statusElem.textContent = 'Lỗi kết nối';
                        initHandle(); // Still initialize with default value
                    });
            }
            
            // Initialize on page load
            window.addEventListener('load', () => {
                createMarkers();
                getCurrentVolume();
                
                // Fallback if API fails
                setTimeout(() => {
                    if (!document.querySelector('.volume-slider')) {
                        initHandle();
                    }
                }, 1000);
            });
            
            // Handle window resize
            window.addEventListener('resize', () => {
                initHandle();
            });
            
            // Add swipe to change volume functionality
            let touchStartX = 0;
            let touchEndX = 0;
            
            touchpad.addEventListener('touchstart', (e) => {
                touchStartX = e.touches[0].clientX;
            });
            
            touchpad.addEventListener('touchend', (e) => {
                touchEndX = e.changedTouches[0].clientX;
                handleSwipe();
            });
            
            function handleSwipe() {
                const swipeThreshold = 50;
                const volumeStep = 10;
                
                if (touchEndX < touchStartX - swipeThreshold) {
                    // Swipe left - decrease volume
                    setVolume(currentVolume - volumeStep);
                    updateHandlePosition(currentVolume);
                }
                
                if (touchEndX > touchStartX + swipeThreshold) {
                    // Swipe right - increase volume
                    setVolume(currentVolume + volumeStep);
                    updateHandlePosition(currentVolume);
                }
            }
        </script>
    </body>
    </html>""")

if FLASK_NGROK_AVAILABLE:
    # Route cho touchpad âm lượng
    @app.route('/volume')
    def volume_touchpad():
        return render_template('volume_touchpad.html')

    # API endpoint để lấy âm lượng hiện tại
    @app.route('/getvolume', methods=['GET'])
    def get_volume():
        try:
            # Đảm bảo khởi tạo COM trong thread hiện tại (chỉ trên Windows)
            com_initialized = False
            if platform.system() == "Windows":
                comtypes.CoInitialize()
                com_initialized = True
            
            volume_percent = get_volume_percentage()
            return jsonify({"volume": volume_percent})
        except Exception as e:
            logger.error(f"Lỗi khi lấy âm lượng hiện tại: {e}")
            return jsonify({"volume": 50, "error": str(e)})  # Giá trị mặc định nếu lỗi
        finally:
            # Giải phóng COM (chỉ trên Windows)
            if platform.system() == "Windows" and com_initialized:
                try:
                    comtypes.CoUninitialize()
                except:
                    pass
        
    # API endpoint để đặt âm lượng
    @app.route('/setvolume', methods=['POST'])
    def set_volume():
        try:
            # Đảm bảo khởi tạo COM trong thread hiện tại (chỉ trên Windows)
            com_initialized = False
            if platform.system() == "Windows":
                comtypes.CoInitialize()
                com_initialized = True
            
            data = request.json
            volume_percent = data.get('volume', 50)
            
            # Chuyển từ phần trăm sang giá trị từ 0.0 đến 1.0
            volume_scalar = volume_percent / 100.0
            
            # Đặt âm lượng
            success = set_windows_volume(volume_scalar)
            
            # Lấy giá trị thực tế sau khi đặt để phản hồi
            actual_volume = get_volume_percentage() if success else volume_percent
            
            return jsonify({
                "status": "success" if success else "failed",
                "volume": actual_volume
            })
        except Exception as e:
            logger.error(f"Lỗi khi đặt âm lượng: {e}")
            return jsonify({
                "status": "failed", 
                "volume": volume_percent, 
                "error": str(e)
            })
        finally:
            # Giải phóng COM (chỉ trên Windows)
            if platform.system() == "Windows" and com_initialized:
                try:
                    comtypes.CoUninitialize()
                except:
                    pass

# Hàm hỗ trợ để lấy và đặt âm lượng hệ thống
def get_windows_volume_interface():
    """Lấy interface điều khiển âm lượng của Windows"""
    if not PYCAW_AVAILABLE or platform.system() != "Windows":
        return None
        
    try:
        # Khởi tạo COM trước khi truy cập các API âm thanh của Windows
        comtypes.CoInitialize()
        
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        return volume
    except Exception as e:
        logger.error(f"Lỗi khi lấy interface âm lượng: {e}")
        return None
    finally:
        # Giải phóng tài nguyên COM sau khi sử dụng
        try:
            comtypes.CoUninitialize()
        except:
            pass

def get_current_volume():
    """Lấy mức âm lượng hiện tại (0.0 đến 1.0)"""
    if not PYCAW_AVAILABLE or platform.system() != "Windows":
        return 0.5
        
    try:
        # Khởi tạo COM trước khi truy cập
        com_initialized = False
        comtypes.CoInitialize()
        com_initialized = True
        
        volume = get_windows_volume_interface()
        if volume:
            current_volume = volume.GetMasterVolumeLevelScalar()
            return current_volume
        return 0.5  # Giá trị mặc định nếu không lấy được
    except Exception as e:
        logger.error(f"Lỗi khi lấy mức âm lượng: {e}")
        return 0.5
    finally:
        # Giải phóng tài nguyên COM
        if com_initialized:
            try:
                comtypes.CoUninitialize()
            except:
                pass

def set_windows_volume(volume_level):
    """Đặt mức âm lượng (0.0 đến 1.0)"""
    if not PYCAW_AVAILABLE or platform.system() != "Windows":
        return False
        
    try:
        # Khởi tạo COM trước khi truy cập
        com_initialized = False
        comtypes.CoInitialize()
        com_initialized = True
        
        # Đảm bảo giá trị âm lượng nằm trong khoảng hợp lệ
        volume_level = max(0.0, min(1.0, volume_level))
        
        # Lấy interface âm lượng
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        # Đặt âm lượng
        volume.SetMasterVolumeLevelScalar(volume_level, None)
        return True
    except Exception as e:
        logger.error(f"Lỗi khi đặt mức âm lượng: {e}")
        return False
    finally:
        # Giải phóng tài nguyên COM
        if com_initialized:
            try:
                comtypes.CoUninitialize()
            except:
                pass

def get_volume_percentage():
    """Lấy mức âm lượng dưới dạng phần trăm"""
    if not PYCAW_AVAILABLE or platform.system() != "Windows":
        return 50
        
    try:
        volume_scalar = get_current_volume()
        return round(volume_scalar * 100)
    except Exception as e:
        logger.error(f"Lỗi khi tính phần trăm âm lượng: {e}")
        return 50  # Giá trị mặc định

# LỆNH MOUSE VIRTUAL SYSTEM
async def mouse_virtual_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Khởi động touchpad ảo qua Ngrok và gửi URL"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
        
    global current_touchpad_type, active_touchpad_chat_id, flask_server_thread, ngrok_tunnel, touchpad_active
    user_id = update.effective_user.id
        
    # Kiểm tra xem Flask và Ngrok có sẵn không
    if not FLASK_NGROK_AVAILABLE:
        await update.message.reply_text(
            get_text("touchpad.missing_libs", user_id=user_id),
            parse_mode="HTML"
        )
        return
        
    # Kiểm tra xem mouse controller có khả dụng không
    if not mouse:
        await update.message.reply_text(
            get_text("touchpad.mouse_init_error", user_id=user_id),
            parse_mode="HTML"
        )
        return
    
    # Kiểm tra nếu có touchpad khác đang chạy
    if current_touchpad_type is not None and touchpad_active:
        # Nếu đang chạy chính touchpad này, chỉ cần gửi lại URL
        if current_touchpad_type == "mouse" and active_touchpad_chat_id == update.effective_chat.id and ngrok_tunnel:
            reply_markup = create_refresh_keyboard(user_id)
            
            await update.message.reply_text(
                get_text("touchpad.already_running", user_id=user_id, url=ngrok_tunnel.public_url),
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            return
        
        # Thông báo đang dừng touchpad cũ
        status_message = await update.message.reply_text(
            get_text("touchpad.stopping_current", user_id=user_id, type=current_touchpad_type),
            parse_mode="HTML"
        )
        
        # Dừng touchpad hiện tại
        success, message = await stop_current_touchpad(update, context)
        if not success:
            await status_message.edit_text(
                get_text("touchpad.cannot_stop", user_id=user_id, message=message),
                parse_mode="HTML"
            )
            return
        
        # Cập nhật thông báo
        await status_message.edit_text(
            get_text("touchpad.stopped_starting_new", user_id=user_id, message=message),
            parse_mode="HTML"
        )
    else:
        # Thông báo khởi động
        status_message = await update.message.reply_text(
            get_text("touchpad.starting", user_id=user_id),
            parse_mode="HTML"
        )
    
    try:
        # Kiểm tra và khởi động Flask server nếu chưa chạy
        if 'flask_server_thread' not in context.bot_data or not context.bot_data['flask_server_thread'] or not context.bot_data['flask_server_thread'].is_alive():
            # Khởi động server Flask trong một thread riêng
            flask_server_thread = Thread(target=start_flask_server)
            flask_server_thread.daemon = True  # Theo dõi luồng chính khi đóng
            flask_server_thread.start()
            context.bot_data['flask_server_thread'] = flask_server_thread
            
            # Thông báo khởi động Flask
            await status_message.edit_text(
                get_text("touchpad.flask_started", user_id=user_id),
                parse_mode="HTML"
            )
            
            # Đợi Flask khởi động
            time.sleep(2)
        
        # Cập nhật biến toàn cục
        current_touchpad_type = "mouse"
        active_touchpad_chat_id = update.effective_chat.id
        touchpad_active = True
        
        # Khởi động Ngrok
        try:
            # Khởi động Ngrok và lấy URL
            public_url = start_ngrok()
            
            if not public_url:
                await status_message.edit_text(
                    get_text("touchpad.ngrok_error", user_id=user_id),
                    parse_mode="HTML"
                )
                # Reset biến
                current_touchpad_type = None
                active_touchpad_chat_id = None
                touchpad_active = False
                return
                
            # Tạo nút làm mới kết nối
            reply_markup = create_refresh_keyboard(user_id)
            
            # Gửi URL và hướng dẫn
            await status_message.edit_text(
                get_text("touchpad.ready", user_id=user_id, url=public_url),
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Lỗi khi khởi động Ngrok: {e}")
            # Xử lý lỗi khi khởi động Ngrok
            await status_message.edit_text(
                get_text("touchpad.error_ngrok", user_id=user_id, error=str(e)),
                parse_mode="HTML"
            )
            # Reset biến
            current_touchpad_type = None
            active_touchpad_chat_id = None
            touchpad_active = False
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo touchpad ảo: {e}")
        # Xử lý lỗi chung
        await status_message.edit_text(
            get_text("touchpad.error_init", user_id=user_id, error=str(e)),
            parse_mode="HTML"
        )
        # Reset biến
        current_touchpad_type = None
        active_touchpad_chat_id = None
        touchpad_active = False

# Xử lý nút làm mới touchpad
async def refresh_touchpad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Làm mới kết nối Ngrok"""
    global ngrok_tunnel, current_touchpad_type, active_touchpad_chat_id, touchpad_active
    
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
    
    user_id = update.effective_user.id
    
    # Kiểm tra xem Flask và Ngrok có sẵn không
    if not FLASK_NGROK_AVAILABLE:
        await query.edit_message_text(
            get_text("touchpad.missing_libs", user_id=user_id),
            parse_mode="HTML"
        )
        return
    
    # Kiểm tra xem có touchpad đang chạy không
    if not current_touchpad_type or not touchpad_active:
        await query.edit_message_text(
            get_text("touchpad.none_running", user_id=user_id),
            parse_mode="HTML"
        )
        return
    
    # Thông báo đang làm mới
    await query.edit_message_text(
        get_text("touchpad.refreshing", user_id=user_id),
        parse_mode="HTML"
    )
    
    try:
        # Dừng Ngrok hiện tại
        stop_ngrok()
        
        # Khởi động lại Ngrok
        public_url = start_ngrok()
        
        if not public_url:
            await query.edit_message_text(
                get_text("touchpad.refresh_error", user_id=user_id),
                parse_mode="HTML"
            )
            # Reset biến
            current_touchpad_type = None
            active_touchpad_chat_id = None
            touchpad_active = False
            return
        
        # Tùy chỉnh thông báo dựa trên loại touchpad
        touchpad_type = current_touchpad_type
        action_info = ""
        endpoint = ""
        callback_data = ""
        
        if touchpad_type == "mouse":
            action_info = get_text("touchpad.mouse_instruction", user_id=user_id)
            callback_data = "refresh_touchpad"
            endpoint = ""
        elif touchpad_type == "volume":
            action_info = get_text("touchpad.volume_instruction", user_id=user_id)
            callback_data = "refresh_volume_touchpad"
            endpoint = "/volume"
        else:
            # Trường hợp không xác định
            await query.edit_message_text(
                get_text("touchpad.invalid_type", user_id=user_id),
                parse_mode="HTML"
            )
            return
            
        # Tạo lại nút làm mới
        keyboard = [
            [InlineKeyboardButton(get_text("buttons.refresh_connection", user_id=user_id), callback_data=callback_data)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Gửi thông báo với URL mới
        await query.edit_message_text(
            get_text("touchpad.refresh_success", user_id=user_id, url=public_url, endpoint=endpoint, action_info=action_info),
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Lỗi khi làm mới kết nối Ngrok: {e}")
        await query.edit_message_text(
            get_text("touchpad.refresh_error_general", user_id=user_id, error=str(e)),
            parse_mode="HTML"
        )
        # Reset biến khi có lỗi
        current_touchpad_type = None
        active_touchpad_chat_id = None
        touchpad_active = False

# Lệnh touchpad điều chỉnh âm lượng
async def volume_virtual_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Khởi động touchpad điều chỉnh âm lượng qua Ngrok và gửi URL"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
    
    global current_touchpad_type, active_touchpad_chat_id, flask_server_thread, ngrok_tunnel, touchpad_active
    user_id = update.effective_user.id
    
    # Kiểm tra xem Flask và Ngrok có sẵn không
    if not FLASK_NGROK_AVAILABLE:
        await update.message.reply_text(
            get_text("touchpad.missing_libs", user_id=user_id),
            parse_mode="HTML"
        )
        return
        
    # Kiểm tra xem pycaw có sẵn không
    if not PYCAW_AVAILABLE or platform.system() != "Windows":
        await update.message.reply_text(
            get_text("touchpad.pycaw_error", user_id=user_id),
            parse_mode="HTML"
        )
        return
    
    # Kiểm tra nếu có touchpad khác đang chạy
    if current_touchpad_type is not None and touchpad_active:
        # Nếu đang chạy chính touchpad này, chỉ cần gửi lại URL
        if current_touchpad_type == "volume" and active_touchpad_chat_id == update.effective_chat.id and ngrok_tunnel:
            reply_markup = create_refresh_keyboard(user_id, "refresh_volume_touchpad")
            
            await update.message.reply_text(
                get_text("touchpad.volume_already_running", user_id=user_id, url=ngrok_tunnel.public_url),
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            return
        
        # Thông báo đang dừng touchpad cũ
        status_message = await update.message.reply_text(
            get_text("touchpad.stopping_current", user_id=user_id, type=current_touchpad_type),
            parse_mode="HTML"
        )
        
        # Dừng touchpad hiện tại
        success, message = await stop_current_touchpad(update, context)
        if not success:
            await status_message.edit_text(
                get_text("touchpad.cannot_stop", user_id=user_id, message=message),
                parse_mode="HTML"
            )
            return
        
        # Cập nhật thông báo
        await status_message.edit_text(
            get_text("touchpad.stopped_volume_new", user_id=user_id, message=message),
            parse_mode="HTML"
        )
    else:
        # Thông báo khởi động
        status_message = await update.message.reply_text(
            get_text("touchpad.starting_volume", user_id=user_id),
            parse_mode="HTML"
        )
    
    try:
        # Kiểm tra và khởi động Flask server nếu chưa chạy
        if 'flask_server_thread' not in context.bot_data or not context.bot_data['flask_server_thread'] or not context.bot_data['flask_server_thread'].is_alive():
            # Khởi động server Flask trong một thread riêng
            flask_server_thread = Thread(target=start_flask_server)
            flask_server_thread.daemon = True  # Theo dõi luồng chính khi đóng
            flask_server_thread.start()
            context.bot_data['flask_server_thread'] = flask_server_thread
            
            # Thông báo khởi động Flask
            await status_message.edit_text(
                get_text("touchpad.flask_started", user_id=user_id),
                parse_mode="HTML"
            )
            
            # Đợi Flask khởi động
            time.sleep(2)
        
        # Cập nhật biến toàn cục
        current_touchpad_type = "volume"
        active_touchpad_chat_id = update.effective_chat.id
        touchpad_active = True
        
        # Khởi động Ngrok
        try:
            # Khởi động Ngrok và lấy URL
            public_url = start_ngrok()
            
            if not public_url:
                await status_message.edit_text(
                    get_text("touchpad.ngrok_error", user_id=user_id),
                    parse_mode="HTML"
                )
                # Reset biến
                current_touchpad_type = None
                active_touchpad_chat_id = None
                touchpad_active = False
                return
            
            # Tạo button làm mới
            reply_markup = create_refresh_keyboard(user_id, "refresh_volume_touchpad")
            
            # Gửi URL và hướng dẫn
            await status_message.edit_text(
                get_text("touchpad.volume_ready", user_id=user_id, url=public_url),
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Lỗi khi khởi động Ngrok: {e}")
            # Xử lý lỗi khi khởi động Ngrok
            await status_message.edit_text(
                get_text("touchpad.error_ngrok", user_id=user_id, error=str(e)),
                parse_mode="HTML"
            )
            # Reset biến
            current_touchpad_type = None
            active_touchpad_chat_id = None
            touchpad_active = False
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo touchpad âm lượng: {e}")
        # Xử lý lỗi chung
        await status_message.edit_text(
            get_text("touchpad.volume_error_init", user_id=user_id, error=str(e)),
            parse_mode="HTML"
        )
        # Reset biến
        current_touchpad_type = None
        active_touchpad_chat_id = None
        touchpad_active = False

# Xử lý nút làm mới touchpad âm lượng
async def refresh_volume_touchpad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Làm mới kết nối Ngrok cho touchpad âm lượng"""
    global ngrok_tunnel, current_touchpad_type, active_touchpad_chat_id, touchpad_active
    
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
    
    user_id = update.effective_user.id
    
    # Kiểm tra xem Flask và Ngrok có sẵn không
    if not FLASK_NGROK_AVAILABLE:
        await query.edit_message_text(
            get_text("touchpad.missing_libs", user_id=user_id),
            parse_mode="HTML"
        )
        return
    
    # Kiểm tra xem có touchpad đang chạy không
    if current_touchpad_type != "volume" or not touchpad_active:
        await query.edit_message_text(
            get_text("touchpad.no_volume_touchpad", user_id=user_id),
            parse_mode="HTML"
        )
        return
    
    # Thông báo đang làm mới
    await query.edit_message_text(
        get_text("touchpad.refreshing", user_id=user_id),
        parse_mode="HTML"
    )
    
    try:
        # Dừng Ngrok hiện tại
        stop_ngrok()
        
        # Khởi động lại Ngrok
        public_url = start_ngrok()
        
        if not public_url:
            await query.edit_message_text(
                get_text("touchpad.refresh_error", user_id=user_id),
                parse_mode="HTML"
            )
            # Reset biến
            current_touchpad_type = None
            active_touchpad_chat_id = None
            touchpad_active = False
            return
        
        # Tạo lại nút làm mới
        keyboard = [
            [InlineKeyboardButton(get_text("buttons.refresh_connection", user_id=user_id), callback_data="refresh_volume_touchpad")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Gửi thông báo với URL mới
        await query.edit_message_text(
            get_text("touchpad.refresh_success", 
                   user_id=user_id, 
                   url=public_url, 
                   endpoint="/volume", 
                   action_info=get_text("touchpad.volume_instruction", user_id=user_id)),
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Lỗi khi làm mới kết nối volume touchpad: {e}")
        await query.edit_message_text(
            get_text("touchpad.refresh_error_general", user_id=user_id, error=str(e)),
            parse_mode="HTML"
        )
        # Reset biến khi có lỗi
        current_touchpad_type = None
        active_touchpad_chat_id = None
        touchpad_active = False

# Lệnh dừng touchpad đang chạy
async def stop_touchpad_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dừng touchpad đang chạy (mouse hoặc volume)"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
    
    global current_touchpad_type, touchpad_active
    user_id = update.effective_user.id
    
    # Kiểm tra xem có touchpad nào đang chạy không
    if current_touchpad_type is None or not touchpad_active:
        await update.message.reply_text(
            get_text("touchpad.none_running_stop", user_id=user_id),
            parse_mode="HTML"
        )
        return
    
    # Thông báo đang dừng
    status_message = await update.message.reply_text(
        get_text("touchpad.stopping", user_id=user_id, type=current_touchpad_type),
        parse_mode="HTML"
    )
    
    # Dừng touchpad
    success, message = await stop_current_touchpad(update, context)
    
    if success:
        await status_message.edit_text(
            get_text("touchpad.stop_success", user_id=user_id, message=message),
            parse_mode="HTML"
        )
    else:
        await status_message.edit_text(
            get_text("touchpad.stop_error", user_id=user_id, message=message),
            parse_mode="HTML"
        )

# Hàm hiển thị bàn phím mô phỏng
async def keyboard_emulator(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Hiển thị bàn phím ảo để điều khiển máy tính"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
        
    user_id = update.effective_user.id
        
    # Tạo bàn phím với bố cục QWERTY
    keyboard = [
        # Hàng 1: QWERTYUIOP
        [KeyboardButton('q'), KeyboardButton('w'), KeyboardButton('e'), KeyboardButton('r'), KeyboardButton('t'),
         KeyboardButton('y'), KeyboardButton('u'), KeyboardButton('i'), KeyboardButton('o'), KeyboardButton('p')],
        
        # Hàng 2: ASDFGHJKL
        [KeyboardButton('a'), KeyboardButton('s'), KeyboardButton('d'), KeyboardButton('f'), KeyboardButton('g'),
         KeyboardButton('h'), KeyboardButton('j'), KeyboardButton('k'), KeyboardButton('l')],
        
        # Hàng 3: ZXCVBNM
        [KeyboardButton('z'), KeyboardButton('x'), KeyboardButton('c'), KeyboardButton('v'), KeyboardButton('b'),
         KeyboardButton('n'), KeyboardButton('m')],
        
        # Hàng 4: Backspace giữa, Space ở giữa, Enter ở phải
        [KeyboardButton('Backspace'), KeyboardButton('space'), KeyboardButton('Enter')]
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        get_text("keyboard.instruction", user_id=user_id),
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

# Xử lý khi người dùng nhấn phím
async def handle_key_press(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý phím được nhấn từ bàn phím ảo"""
    # Kiểm tra người dùng có được phép không
    if not await check_user_permission(update):
        return
        
    # Bỏ qua các lệnh
    if update.message.text.startswith('/'):
        return
        
    user_id = update.effective_user.id
    user_input = update.message.text  # Lấy nội dung từ phím bấm

    # Mô phỏng nhấn phím với pyautogui
    try:
        if user_input == 'Backspace':
            pyautogui.press('backspace')  # Mô phỏng nhấn phím Backspace
        elif user_input == 'Enter':
            pyautogui.press('enter')  # Mô phỏng nhấn phím Enter
        elif user_input == 'space':
            pyautogui.press('space')  # Mô phỏng nhấn phím Space
        else:
            pyautogui.typewrite(user_input)  # Mô phỏng nhấn các phím chữ thường
        
        await update.message.reply_text(
            get_text("keyboard.key_pressed", user_id=user_id, key=user_input),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Lỗi khi mô phỏng nhấn phím: {e}")
        await update.message.reply_text(
            get_text("keyboard.key_error", user_id=user_id, error=str(e)),
            parse_mode="HTML"
        )

# LỆNH CHỌN NGÔN NGỮ
async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hiển thị menu chọn ngôn ngữ"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
        
    user_id = update.effective_user.id
    current_language = get_user_language(user_id)
    
    # Tạo hai nút chọn ngôn ngữ
    reply_markup = create_language_keyboard()
    
    # Hiển thị menu chọn ngôn ngữ
    await update.message.reply_text(
        get_text("messages.set_language_title", user_id=user_id) + "\n" +
        (get_text("messages.current_language", user_id=user_id)),
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

# Xử lý khi người dùng chọn ngôn ngữ
async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý khi người dùng chọn ngôn ngữ"""
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
    
    user_id = update.effective_user.id
    current_language = get_user_language(user_id)
    selected_language = query.data.split("_")[1]  # lang_vi -> vi, lang_en -> en
    
    # Nếu chọn ngôn ngữ đang dùng, không làm gì
    if current_language == selected_language:
        await query.edit_message_text(
            get_text("messages.already_using_language", user_id=user_id),
            parse_mode="HTML"
        )
        return
    
    # Đặt ngôn ngữ mới cho người dùng
    set_user_language(user_id, selected_language)
    
    # Thông báo đã thay đổi ngôn ngữ - sử dụng ngôn ngữ mới đã chọn
    await query.edit_message_text(
        get_text("messages.language_changed", user_id=user_id),
        parse_mode="HTML"
    )
    
    # Cập nhật các lệnh của bot (bot commands) dựa trên ngôn ngữ mới
    commands = [BotCommand(command, desc) for command, desc in get_commands(user_id).items()]
    try:
        await context.bot.set_my_commands(commands)
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật danh sách lệnh: {e}")

# QUẢN LÝ TRÌNH DUYỆT (PLAYWRIGHT)

# Khởi tạo Playwright và mở trình duyệt
async def initialize_browser():
    """Khởi tạo trình duyệt sử dụng Playwright"""
    global playwright, browser, page, current_browser_type

    try:
        # Đóng browser hiện tại nếu đang mở
        await close_browser()
        
        # Khởi tạo Playwright
        playwright = await async_playwright().start()
        
        # Chọn trình duyệt dựa trên current_browser_type
        browser_paths = BROWSER_PATHS
        user_data_paths = USER_DATA_DIRS
        
        # Kiểm tra xem trình duyệt hiện tại có tồn tại không
        if current_browser_type not in browser_paths or not os.path.exists(browser_paths[current_browser_type]):
            # Tìm trình duyệt thay thế
            available_browsers = [b for b in browser_paths if os.path.exists(browser_paths[b])]
            if not available_browsers:
                return False, "Không tìm thấy trình duyệt nào được cài đặt trên hệ thống."
            
            current_browser_type = available_browsers[0]
            logger.info(f"Đã chuyển sang trình duyệt thay thế: {current_browser_type}")
        
        # Edge có xử lý đặc biệt
        if current_browser_type == "edge":
            try:
                # Sử dụng playwright.chromium với channel="msedge"
                logger.info("Đang khởi động Microsoft Edge...")
                
                # Phương pháp 1: Sử dụng chế độ incognito (không dùng user data)
                browser = await playwright.chromium.launch(
                    channel="msedge",
                    headless=False,
                    args=["--no-sandbox"]
                )
                
                # Mở một context mới (tương đương incognito)
                browser_context = await browser.new_context()
                
                # Tạo trang mới
                page = await browser_context.new_page()
                return True, "Khởi tạo trình duyệt Edge thành công (chế độ ẩn danh)"
                
            except Exception as edge_error:
                # Phương pháp 2: Thử với browser mặc định nếu Edge thất bại
                error_msg = str(edge_error)
                logger.error(f"Lỗi khi khởi động Edge: {error_msg}")
                
                # Tự động chuyển sang Brave hoặc Chrome nếu Edge không hoạt động
                # Thử Brave trước
                if "brave" in browser_paths and os.path.exists(browser_paths["brave"]):
                    current_browser_type = "brave"
                # Nếu không có Brave, thử Chrome
                elif "chrome" in browser_paths and os.path.exists(browser_paths["chrome"]):
                    current_browser_type = "chrome"
                else:
                    # Nếu không có cả Brave và Chrome, trả về lỗi
                    return False, f"Microsoft Edge gặp lỗi và không tìm thấy trình duyệt thay thế: {error_msg}"
                
                # Thông báo lỗi và biện pháp khắc phục đã thực hiện
                error_info = (
                    f"Microsoft Edge gặp lỗi: {error_msg.replace('<', '&lt;').replace('>', '&gt;')}\n\n"
                    f"Bot sẽ tự động chuyển sang trình duyệt {current_browser_type.capitalize()}.\n\n"
                    f"Gợi ý: Để Edge hoạt động, thử chạy bot với quyền admin hoặc đóng tất cả cửa sổ Edge đang mở trước."
                )
                
                # Tiếp tục với trình duyệt thay thế
                browser_type = playwright.chromium
                executable_path = browser_paths[current_browser_type]
                user_data_dir = user_data_paths[current_browser_type]
                
                if not os.path.exists(executable_path):
                    return False, f"Không tìm thấy trình duyệt {current_browser_type.capitalize()} tại: {executable_path}"
                
                if not os.path.exists(user_data_dir):
                    # Nếu không tìm thấy thư mục dữ liệu, tạo mới
                    try:
                        os.makedirs(user_data_dir, exist_ok=True)
                    except:
                        return False, f"Không thể tạo thư mục dữ liệu người dùng: {user_data_dir}"
                
                try:
                    browser = await browser_type.launch_persistent_context(
                        user_data_dir,
                        executable_path=executable_path,
                        headless=False
                    )
                    
                    # Tạo trang mới
                    page = await browser.new_page()
                    return True, f"Edge gặp lỗi. Đã tự động chuyển sang {current_browser_type.capitalize()}. {error_info}"
                except Exception as browser_error:
                    return False, f"Không thể khởi động trình duyệt {current_browser_type.capitalize()} dự phòng: {str(browser_error)}"
        
        # Xử lý các trình duyệt khác
        else:
            browser_type = playwright.chromium
            executable_path = browser_paths[current_browser_type]
            
            # Kiểm tra đường dẫn user data
            user_data_dir = user_data_paths[current_browser_type]
            if not os.path.exists(user_data_dir):
                # Nếu không tìm thấy thư mục dữ liệu, tạo mới
                try:
                    os.makedirs(user_data_dir, exist_ok=True)
                except:
                    return False, f"Không thể tạo thư mục dữ liệu người dùng: {user_data_dir}"
            
            # Khởi tạo trình duyệt
            try:
                browser = await browser_type.launch_persistent_context(
                    user_data_dir,
                    executable_path=executable_path,
                    headless=False
                )
                
                # Tạo trang mới
                page = await browser.new_page()
                return True, f"Khởi tạo trình duyệt {current_browser_type.capitalize()} thành công"
            except Exception as e:
                return False, f"Không thể khởi động trình duyệt {current_browser_type.capitalize()}: {str(e)}"
    except Exception as e:
        # Xử lý thông báo lỗi an toàn cho HTML
        error_msg = str(e)
        safe_error = error_msg.replace("<", "&lt;").replace(">", "&gt;")
        return False, f"Lỗi khi khởi tạo trình duyệt: {safe_error}"

# Đóng browser
async def close_browser():
    """Đóng trình duyệt và giải phóng tài nguyên"""
    global browser, page, playwright
    
    try:
        if page:
            await page.close()
            page = None
        
        if browser:
            await browser.close()
            browser = None
        
        if playwright:
            await playwright.stop()
            playwright = None
            
        return True, "Đã đóng trình duyệt"
    except Exception as e:
        return False, f"Lỗi khi đóng trình duyệt: {str(e)}"

# Lệnh chọn trình duyệt mặc định
async def set_browser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chọn trình duyệt mặc định"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
        
    global current_browser_type
    user_id = update.effective_user.id

    if not context.args:
        # Tạo danh sách trình duyệt có sẵn
        available_browsers = {}
        for browser_name, browser_path in BROWSER_PATHS.items():
            if os.path.exists(browser_path):
                available_browsers[browser_name] = browser_path
        
        # Nếu không có trình duyệt nào
        if not available_browsers:
            await update.message.reply_text(
                get_text("browser.no_browsers", user_id=user_id),
                parse_mode="HTML"
            )
            return
        
        # Tạo các nút cho trình duyệt có sẵn
        reply_markup = create_browser_selection_keyboard(user_id, available_browsers)
        
        await update.message.reply_text(
            get_text("browser.current_browser", user_id=user_id, browser=current_browser_type.capitalize()),
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return

    browser_choice = context.args[0].lower()
    
    # Kiểm tra xem trình duyệt có tồn tại không
    if browser_choice in BROWSER_PATHS and os.path.exists(BROWSER_PATHS[browser_choice]):
        current_browser_type = browser_choice
        
        message = get_text("browser.set_success", user_id=user_id, browser=browser_choice.capitalize())
        
        if browser_choice == "edge":
            message += get_text("browser.edge_note", user_id=user_id)
            
        await update.message.reply_text(
            message,
            parse_mode="HTML"
        )
    else:
        # Kiểm tra xem trình duyệt có trong danh sách nhưng không tồn tại
        if browser_choice in BROWSER_PATHS:
            await update.message.reply_text(
                get_text("browser.browser_not_found", user_id=user_id, 
                       browser=browser_choice.capitalize(), 
                       path=BROWSER_PATHS[browser_choice]),
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                get_text("browser.invalid_browser", user_id=user_id),
                parse_mode="HTML"
            )

# Xử lý callback chọn trình duyệt
async def handle_browser_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý khi người dùng chọn trình duyệt từ inline button"""
    global current_browser_type
    
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
    
    user_id = update.effective_user.id
    
    if not query.data.startswith("browser_"):
        return
        
    browser_choice = query.data.split("_")[1]
    
    # Kiểm tra xem trình duyệt có tồn tại không
    if browser_choice in BROWSER_PATHS and os.path.exists(BROWSER_PATHS[browser_choice]):
        current_browser_type = browser_choice
        
        message = get_text("browser.set_success", user_id=user_id, browser=browser_choice.capitalize())
        
        if browser_choice == "edge":
            message += get_text("browser.edge_note", user_id=user_id)
            
        await query.edit_message_text(
            message,
            parse_mode="HTML"
        )
    else:
        # Kiểm tra xem trình duyệt có trong danh sách nhưng không tồn tại
        if browser_choice in BROWSER_PATHS:
            await query.edit_message_text(
                get_text("browser.browser_not_found", user_id=user_id, 
                       browser=browser_choice.capitalize(), 
                       path=BROWSER_PATHS[browser_choice]),
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text(
                get_text("browser.invalid_browser", user_id=user_id),
                parse_mode="HTML"
            )

# ĐIỀU KHIỂN TRÌNH DUYỆT

# Tính năng phát video
async def play_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mở video YouTube và hiển thị các điều khiển"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
        
    global page
    user_id = update.effective_user.id
    
    # Lấy link từ tham số hoặc tin nhắn
    if context.args:
        youtube_url = context.args[0]
    else:
        youtube_url = update.message.text.strip()
        if youtube_url.startswith("/playvideo "):
            youtube_url = youtube_url[11:].strip()
        else:
            await update.message.reply_text(
                get_text("browser.youtube_link_help", user_id=user_id),
                parse_mode="HTML"
            )
            return
    
    # Kiểm tra link YouTube hợp lệ
    youtube_pattern = r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+" 
    if not re.match(youtube_pattern, youtube_url):
        await update.message.reply_text(
            get_text("browser.invalid_youtube", user_id=user_id),
            parse_mode="HTML"
        )
        return
    
    try:
        # Kiểm tra nếu trình duyệt đã khởi tạo chưa
        if not browser or not page:
            init_message = await update.message.reply_text(
                get_text("browser.starting_browser", user_id=user_id, browser=current_browser_type.capitalize()),
                parse_mode="HTML"
            )
            success, message = await initialize_browser()
            if not success:
                # Đảm bảo thông báo lỗi an toàn cho HTML
                safe_message = message.replace("<", "&lt;").replace(">", "&gt;")
                await init_message.edit_text(
                    get_text("browser.browser_error", user_id=user_id, error=safe_message),
                    parse_mode="HTML"
                )
                return
            else:
                await init_message.edit_text(
                    get_text("browser.browser_started", user_id=user_id, browser=current_browser_type.capitalize()),
                    parse_mode="HTML"
                )
        
        # Điều hướng đến trang YouTube
        loading_message = await update.message.reply_text(
            get_text("browser.opening_video", user_id=user_id, browser=current_browser_type.capitalize()),
            parse_mode="HTML"
        )
        
        try:
            await page.goto(youtube_url, timeout=30000)  # Timeout 30 giây
            
            # Chờ video load
            try:
                await page.wait_for_selector("video", state="attached", timeout=15000)
                await loading_message.edit_text(
                    get_text("browser.video_opened", user_id=user_id, browser=current_browser_type.capitalize()),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Không tìm thấy trình phát video: {e}")
                await loading_message.edit_text(
                    get_text("browser.video_not_found", user_id=user_id),
                    parse_mode="HTML"
                )
            
            # Tạo các nút điều khiển
            reply_markup = create_video_controls_keyboard(user_id)
            await update.message.reply_text(
                get_text("browser.select_action", user_id=user_id),
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Lỗi khi mở URL {youtube_url}: {e}")
            await loading_message.edit_text(
                get_text("browser.url_error", user_id=user_id),
                parse_mode="HTML"
            )
            
    except Exception as e:
        # Đảm bảo thông báo lỗi an toàn cho HTML
        error_msg = str(e)
        safe_error = error_msg.replace("<", "&lt;").replace(">", "&gt;")
        await update.message.reply_text(
            get_text("browser.general_error", user_id=user_id, error=safe_error),
            parse_mode="HTML"
        )

# Xử lý button điều khiển video
async def video_controls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý các button điều khiển video"""
    global page, browser
    
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra quyền người dùng thông qua update
    if not await check_user_permission(update):
        return
    
    user_id = update.effective_user.id
    
    # Kiểm tra xem page có tồn tại không
    if not page:
        await query.edit_message_text(
            get_text("browser.no_browser_open", user_id=user_id),
            parse_mode="HTML"
        )
        return
    
    action = query.data
    try:
        if action == "play_pause":
            # Thực thi JavaScript để phát/tạm dừng video
            await page.evaluate("document.querySelector('video').paused ? document.querySelector('video').play() : document.querySelector('video').pause()")
            await query.edit_message_text(
                get_text("browser.play_pause", user_id=user_id),
                parse_mode="HTML"
            )
            
        elif action == "rewind":
            # Tua lại 10 giây
            await page.evaluate("document.querySelector('video').currentTime -= 10")
            await query.edit_message_text(
                get_text("browser.rewind", user_id=user_id),
                parse_mode="HTML"
            )
            
        elif action == "forward":
            # Tua tiến 10 giây
            await page.evaluate("document.querySelector('video').currentTime += 10")
            await query.edit_message_text(
                get_text("browser.forward", user_id=user_id),
                parse_mode="HTML"
            )
            
        elif action == "close_browser":
            # Đóng trình duyệt
            success, message = await close_browser()
            await query.edit_message_text(
                get_text("browser.browser_closed", user_id=user_id, browser=current_browser_type.capitalize()),
                parse_mode="HTML"
            )
            return
            
        # Lưu lại và giữ các nút điều khiển video luôn hoạt động (trừ khi đã đóng toàn bộ)
        if action != "close_browser":
            reply_markup = create_video_controls_keyboard(user_id)
            await query.edit_message_reply_markup(reply_markup=reply_markup)
            
    except Exception as e:
        await query.edit_message_text(
            get_text("browser.video_control_error", user_id=user_id, error=str(e)),
            parse_mode="HTML"
        )

# Lệnh mở web tùy chỉnh
async def open_web(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mở một trang web và hiển thị các điều khiển"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
        
    global page
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            get_text("browser.setbrowser_help", user_id=user_id),
            parse_mode="HTML"
        )
        return
    
    url = " ".join(context.args).strip()
    
    try:
        # Kiểm tra nếu trình duyệt đã khởi tạo chưa
        if not browser or not page:
            init_message = await update.message.reply_text(
                get_text("browser.starting_browser", user_id=user_id, browser=current_browser_type.capitalize()),
                parse_mode="HTML"
            )
            success, message = await initialize_browser()
            if not success:
                # Đảm bảo thông báo lỗi an toàn cho HTML
                safe_message = message.replace("<", "&lt;").replace(">", "&gt;")
                await init_message.edit_text(
                    get_text("browser.browser_error", user_id=user_id, error=safe_message),
                    parse_mode="HTML"
                )
                return
            else:
                await init_message.edit_text(
                    get_text("browser.browser_started", user_id=user_id, browser=current_browser_type.capitalize()),
                    parse_mode="HTML"
                )
        
        # Thêm http:// nếu cần
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Mở trang web
        loading_message = await update.message.reply_text(
            get_text("browser.opening_website", user_id=user_id, url=url),
            parse_mode="HTML"
        )
        
        try:
            await page.goto(url, timeout=30000)  # Timeout 30 giây
            await loading_message.edit_text(
                get_text("browser.website_opened", user_id=user_id, url=url, browser=current_browser_type.capitalize()),
                parse_mode="HTML"
            )
            
            # Tạo các nút điều khiển
            reply_markup = create_web_controls_keyboard(user_id)
            await update.message.reply_text(
                get_text("browser.select_action", user_id=user_id),
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Lỗi khi mở URL {url}: {e}")
            await loading_message.edit_text(
                get_text("browser.url_error", user_id=user_id),
                parse_mode="HTML"
            )
            
    except Exception as e:
        # Đảm bảo thông báo lỗi an toàn cho HTML
        error_msg = str(e)
        safe_error = error_msg.replace("<", "&lt;").replace(">", "&gt;")
        await update.message.reply_text(
            get_text("browser.general_error", user_id=user_id, error=safe_error),
            parse_mode="HTML"
        )

# Xử lý các nút điều khiển web
async def web_controls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý các button điều khiển trình duyệt"""
    global page
    
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
    
    user_id = update.effective_user.id
    
    # Kiểm tra xem page có tồn tại không
    if not page:
        await query.edit_message_text(
            get_text("browser.no_browser_open", user_id=user_id),
            parse_mode="HTML"
        )
        return
    
    action = query.data
    try:
        if action == "reload_page":
            await page.reload()
            await query.edit_message_text(
                get_text("browser.page_reloaded", user_id=user_id),
                parse_mode="HTML"
            )
            
        elif action == "back_page":
            if await page.evaluate("window.history.length > 1"):
                await page.go_back()
                await query.edit_message_text(
                    get_text("browser.back_success", user_id=user_id),
                    parse_mode="HTML"
                )
            else:
                await query.edit_message_text(
                    get_text("browser.back_error", user_id=user_id),
                    parse_mode="HTML"
                )
            
        elif action == "forward_page":
            can_go_forward = await page.evaluate("window.history.length > 1 && window.history.state !== null")
            if can_go_forward:
                await page.go_forward()
                await query.edit_message_text(
                    get_text("browser.forward_success", user_id=user_id),
                    parse_mode="HTML"
                )
            else:
                await query.edit_message_text(
                    get_text("browser.forward_error", user_id=user_id),
                    parse_mode="HTML"
                )
            
        elif action == "close_browser":
            success, message = await close_browser()
            await query.edit_message_text(
                get_text("browser.browser_closed", user_id=user_id, browser=current_browser_type.capitalize()),
                parse_mode="HTML"
            )
            return
            
        # Lưu lại và giữ các nút điều khiển web luôn hoạt động (trừ khi đã đóng toàn bộ)
        if action != "close_browser":
            reply_markup = create_web_controls_keyboard(user_id)
            await query.edit_message_reply_markup(reply_markup=reply_markup)
            
    except Exception as e:
        await query.edit_message_text(
            get_text("browser.web_control_error", user_id=user_id, error=str(e)),
            parse_mode="HTML"
        )

# ĐIỀU KHIỂN HỆ THỐNG

# Lệnh shutdown
async def shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tắt máy tính"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
        
    await ask_confirmation(update, context, "shutdown")

# Lệnh restart
async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Khởi động lại máy tính"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
        
    await ask_confirmation(update, context, "restart")

# Lệnh sleep
async def sleep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Đưa máy tính vào chế độ ngủ"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
        
    await ask_confirmation(update, context, "sleep")

# Lệnh cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hủy lệnh tắt máy hoặc khởi động lại"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
        
    await ask_confirmation(update, context, "cancel")

# Hỏi xác nhận trước khi thực hiện lệnh
async def ask_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, action):
    """Hiển thị nút xác nhận trước khi thực hiện lệnh hệ thống"""
    context.user_data["action"] = action
    user_id = update.effective_user.id
    
    # Thông báo cảnh báo dựa trên loại hành động
    message_key = f"system.confirm_{action}"
    message = get_text(message_key, user_id=user_id)
    
    reply_markup = create_confirmation_keyboard(user_id)
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="HTML")

# Tạo inline button để xác nhận
async def confirm_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý khi người dùng xác nhận lệnh hệ thống"""
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return

    action = context.user_data.get("action")
    user_id = update.effective_user.id
    
    try:
        if action == "shutdown":
            await query.edit_message_text(
                get_text("system.shutdown_progress", user_id=user_id),
                parse_mode="HTML"
            )
            
            # Lệnh tắt máy phụ thuộc vào hệ điều hành
            if platform.system() == "Windows":
                os.system("shutdown /s /t 3")
            else:
                os.system("sudo shutdown -h +1")
                
        elif action == "restart":
            await query.edit_message_text(
                get_text("system.restart_progress", user_id=user_id),
                parse_mode="HTML"
            )
            
            # Lệnh khởi động lại phụ thuộc vào hệ điều hành
            if platform.system() == "Windows":
                os.system("shutdown /r /t 3")
            else:
                os.system("sudo shutdown -r +1")
                
        elif action == "cancel":
            await query.edit_message_text(
                get_text("system.cancel_progress", user_id=user_id),
                parse_mode="HTML"
            )
            
            # Lệnh hủy lệnh tắt phụ thuộc vào hệ điều hành
            result = 0
            if platform.system() == "Windows":
                result = os.system("shutdown -a")
            else:
                result = os.system("sudo shutdown -c")
                
            if result == 0:
                await query.edit_message_text(
                    get_text("system.cancel_success", user_id=user_id),
                    parse_mode="HTML"
                )
            else:
                await query.edit_message_text(
                    get_text("system.cancel_none", user_id=user_id),
                    parse_mode="HTML"
                )
                
        elif action == "sleep":
            await query.edit_message_text(
                get_text("system.sleep_progress", user_id=user_id),
                parse_mode="HTML"
            )
            time.sleep(2)  # Đợi 2 giây để đảm bảo tin nhắn được gửi
            
            # Lệnh ngủ phụ thuộc vào hệ điều hành
            if platform.system() == "Windows":
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            else:
                os.system("systemctl suspend")
                
        else:
            await query.edit_message_text(
                get_text("system.no_action", user_id=user_id),
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Lỗi khi thực hiện lệnh hệ thống: {e}")
        await query.edit_message_text(
            get_text("system.command_error", user_id=user_id, error=str(e)),
            parse_mode="HTML"
        )

async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý khi người dùng hủy lệnh hệ thống"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    await query.edit_message_text(
        get_text("system.action_cancelled", user_id=user_id),
        parse_mode="HTML"
    )

# LỆNH QUẢN LÝ FILE

# Hàm chụp màn hình
def capture_high_quality_screenshot():
    """Chụp màn hình"""
    try:
        # Chụp màn hình bằng pyautogui
        screenshot = pyautogui.screenshot()
        
        # Chuyển sang mảng numpy để xử lý với OpenCV
        screenshot = np.array(screenshot)
        
        # Chuyển từ RGB sang BGR (định dạng của OpenCV)
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
        
        return screenshot
    except Exception as e:
        logger.error(f"Lỗi khi chụp màn hình: {e}")
        try:
            # Trong trường hợp lỗi, thử phương pháp đơn giản hơn
            basic_screenshot = np.array(pyautogui.screenshot())
            return cv2.cvtColor(basic_screenshot, cv2.COLOR_RGB2BGR)
        except Exception as e2:
            logger.error(f"Lỗi nghiêm trọng khi chụp màn hình: {e2}")
            return None

# Hàm quay video màn hình
def record_screen(output_path, duration=30.0, fps=20.0):
    """Hàm ghi màn hình thành video MP4 với thời gian giới hạn"""
    global is_recording
    
    # Lấy kích thước màn hình
    screen_width, screen_height = pyautogui.size()
    
    # Định dạng ghi video
    codecs_to_try = ['avc1', 'H264', 'XVID', 'MJPG', 'mp4v']
    current_codec_index = 0
    
    try:
        # Đảm bảo kích thước là số chẵn (yêu cầu của một số codec)
        if screen_width % 2 == 1:
            screen_width -= 1
        if screen_height % 2 == 1:
            screen_height -= 1
            
        # Thử lần lượt các codec
        out = None
        while current_codec_index < len(codecs_to_try) and (out is None or not out.isOpened()):
            codec = codecs_to_try[current_codec_index]
            fourcc = cv2.VideoWriter_fourcc(*codec)
            
            # Tạo VideoWriter
            out = cv2.VideoWriter(output_path, fourcc, fps, (screen_width, screen_height))
            
            if not out.isOpened():
                current_codec_index += 1
                logger.info(f"Đang thử codec tiếp theo: {codecs_to_try[current_codec_index] if current_codec_index < len(codecs_to_try) else 'None'}")
        
        if not out.isOpened():
            logger.error("Không thể khởi tạo VideoWriter với bất kỳ codec nào")
            return False
            
        # Bắt đầu ghi
        is_recording = True
        start_time = time.time()
        
        frame_count = 0
        while is_recording and (time.time() - start_time) < duration:
            # Chụp màn hình
            img = capture_high_quality_screenshot()
            if img is None:
                logger.error("Không thể chụp màn hình, dừng ghi")
                break
            
            # Ghi frame vào video
            out.write(img)
            frame_count += 1
            
            # Hiển thị tiến trình trong console
            if frame_count % 10 == 0:
                elapsed = time.time() - start_time
                logger.info(f"Đã ghi {frame_count} frames, {elapsed:.1f}s...")
            
            # Đảm bảo đúng fps
            current_time = time.time()
            time_to_sleep = max(0, 1/fps - (current_time - start_time) % (1/fps))
            time.sleep(time_to_sleep)
    
    except Exception as e:
        logger.error(f"Lỗi trong quá trình ghi màn hình: {e}")
        return False
    finally:
        # Kết thúc ghi
        if 'out' in locals() and out is not None:
            out.release()
        cv2.destroyAllWindows()  # Đảm bảo đóng tất cả cửa sổ OpenCV
        
        if 'start_time' in locals() and frame_count > 0:
            duration = time.time() - start_time
            logger.info(f"Đã ghi {duration:.2f} giây video ({frame_count} frames) vào {output_path}")
            return True
        else:
            return False

# Bắt đầu ghi màn hình
def start_recording(output_path):
    """Bắt đầu quay màn hình trong một luồng riêng"""
    global recording_thread, is_recording
    
    # Nếu đang ghi thì dừng lại
    if is_recording:
        stop_recording()
    
    # Bắt đầu ghi trong một luồng mới
    recording_thread = Thread(target=record_screen, args=(output_path,))
    recording_thread.daemon = True
    recording_thread.start()
    
    return True

# Dừng ghi màn hình
def stop_recording():
    """Dừng quay màn hình"""
    global is_recording, recording_thread
    
    if is_recording:
        is_recording = False
        if recording_thread:
            # Đợi luồng ghi kết thúc (tối đa 5 giây)
            recording_thread.join(timeout=5.0)
        recording_thread = None
        return True
    return False

# Hàm gửi ảnh dưới dạng tài liệu
async def send_photo_without_waiting(bot, chat_id, photo_path, original_message):
    """Gửi ảnh màn hình dưới dạng document - tránh lỗi kích thước"""
    try:
        # Lấy tên file từ đường dẫn
        file_name = os.path.basename(photo_path)
        
        # Gửi ảnh dưới dạng document với timeout cao hơn
        with open(photo_path, 'rb') as file:
            await bot.send_document(
                chat_id=chat_id, 
                document=file,
                filename=file_name,
                caption="<b>📸 Ảnh chụp màn hình</b>",
                parse_mode="HTML",
                read_timeout=60,
                write_timeout=60
            )
        
        # Xóa file sau khi gửi
        try:
            os.remove(photo_path)
            logger.info(f"Đã xóa file ảnh tạm: {photo_path}")
        except Exception as e:
            logger.error(f"Lỗi khi xóa file ảnh: {e}")
            
    except Exception as e:
        logger.error(f"Lỗi khi gửi ảnh (trong task riêng): {e}")

# Chụp ảnh màn hình
async def screen_shot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chụp màn hình và gửi về Telegram"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
        
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    file_name = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    screenshot_path = os.path.join(UPLOAD_FOLDER, file_name)

    # Thông báo đang xử lý
    status_message = await update.message.reply_text(
        get_text("screenshot.taking", user_id=user_id),
        parse_mode="HTML"
    )

    try:
        # Chụp màn hình
        img = capture_high_quality_screenshot()
        if img is None:
            await status_message.edit_text(
                get_text("screenshot.error", user_id=user_id),
                parse_mode="HTML"
            )
            return
        
        # Lưu ảnh
        cv2.imwrite(screenshot_path, img, [cv2.IMWRITE_PNG_COMPRESSION, 0])  # 0 = không nén

        # Cập nhật tin nhắn trạng thái
        await status_message.edit_text(
            get_text("screenshot.sending", user_id=user_id),
            parse_mode="HTML"
        )
        
        # Kiểm tra xem file có tồn tại không
        if not os.path.exists(screenshot_path):
            await status_message.edit_text(
                get_text("screenshot.saving_error", user_id=user_id),
                parse_mode="HTML"
            )
            return
            
        # Kiểm tra kích thước file
        file_size = os.path.getsize(screenshot_path) / (1024 * 1024)  # MB
        if file_size > 50:
            await status_message.edit_text(
                get_text("screenshot.size_error", user_id=user_id, size=file_size),
                parse_mode="HTML"
            )
            try:
                os.remove(screenshot_path)
            except:
                pass
            return
        
        # Tạo task để gửi ảnh mà không đợi kết quả
        asyncio.create_task(
            send_photo_without_waiting(
                context.bot, 
                chat_id,
                screenshot_path,
                update.message
            )
        )
        
        # Cập nhật thông báo ngay lập tức
        await status_message.edit_text(
            get_text("screenshot.sending_progress", user_id=user_id),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Lỗi khi chụp và gửi ảnh màn hình: {e}")
        await status_message.edit_text(
            get_text("screenshot.screenshot_error", user_id=user_id, error=str(e)),
            parse_mode="HTML"
        )

# Quay video màn hình
async def record_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bắt đầu ghi video màn hình"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
        
    global is_recording
    user_id = update.effective_user.id
    
    if is_recording:
        await update.message.reply_text(
            get_text("screenshot.already_recording", user_id=user_id),
            parse_mode="HTML"
        )
        return
    
    # Tạo tên file duy nhất với timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(UPLOAD_FOLDER, f"screen_recording_{timestamp}.mp4")
    
    # Thông báo cho người dùng
    status_message = await update.message.reply_text(
        get_text("screenshot.prepare_recording", user_id=user_id),
        parse_mode="HTML"
    )
    
    # Lưu ID tin nhắn trạng thái để cập nhật sau này
    context.user_data["status_message_id"] = status_message.message_id
    context.user_data["chat_id"] = update.effective_chat.id
    
    # Bắt đầu ghi với giới hạn thời gian 30 giây
    success = start_recording(output_path)
    
    if not success:
        await status_message.edit_text(
            get_text("screenshot.start_error", user_id=user_id),
            parse_mode="HTML"
        )
        return
    
    # Lưu thông tin vào context
    context.user_data["recording_path"] = output_path
    
    # Tạo nút dừng ghi
    reply_markup = create_stop_recording_keyboard(user_id)
    
    await update.message.reply_text(
        get_text("screenshot.recording_started", user_id=user_id),
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

# Xử lý dừng quay video
async def handle_stop_recording(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý khi người dùng nhấn nút dừng ghi"""
    global is_recording
    
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
    
    user_id = update.effective_user.id
    
    if not is_recording:
        await query.edit_message_text(
            get_text("screenshot.no_recording", user_id=user_id),
            parse_mode="HTML"
        )
        return
        
    # Cập nhật tin nhắn
    await query.edit_message_text(
        get_text("screenshot.stopping_video", user_id=user_id), 
        reply_markup=query.message.reply_markup,
        parse_mode="HTML"
    )
    
    # Dừng ghi
    is_recording = False
    
    # Đợi thread xử lý xong (đã được xử lý trong stop_recording())
    stopped = stop_recording()
    
    # Đường dẫn video
    recording_path = context.user_data.get("recording_path")
    if not recording_path or not os.path.exists(recording_path):
        await query.edit_message_text(
            get_text("screenshot.video_not_found", user_id=user_id),
            parse_mode="HTML"
        )
        return
        
    # Đợi để đảm bảo file không bị khóa
    time.sleep(1)
        
    # Kiểm tra kích thước file
    try:
        file_size_mb = os.path.getsize(recording_path) / (1024 * 1024)
        
        if file_size_mb > 50:  # Giới hạn của Telegram là 50MB
            await query.edit_message_text(
                get_text("screenshot.size_too_large", user_id=user_id, size=file_size_mb, path=recording_path),
                parse_mode="HTML"
            )
            return
        
        # Kiểm tra file có hợp lệ không
        if file_size_mb < 0.1:  # Nếu file quá nhỏ, có thể bị lỗi
            await query.edit_message_text(
                get_text("screenshot.size_too_small", user_id=user_id, size=file_size_mb),
                parse_mode="HTML"
            )
            # Xóa file lỗi
            try:
                os.remove(recording_path)
            except:
                pass
            return
        
        # Cập nhật thông báo
        await query.edit_message_text(
            get_text("screenshot.sending_video", user_id=user_id),
            parse_mode="HTML"
        )
        
        # Gửi video không đồng bộ và không đợi phản hồi
        try:
            # Khởi tạo một task mới để gửi file mà không đợi
            asyncio.create_task(
                send_video_without_waiting(
                    context.bot,
                    update.effective_chat.id,
                    recording_path,
                    os.path.basename(recording_path)
                )
            )
            
            # Cập nhật thông báo thành công ngay lập tức
            await query.edit_message_text(
                get_text("screenshot.video_sent", user_id=user_id, size=file_size_mb),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Lỗi khi tạo task gửi video: {e}")
            await query.edit_message_text(
                get_text("screenshot.video_error", user_id=user_id, error=str(e), path=recording_path),
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Lỗi khi xử lý video: {e}")
        await query.edit_message_text(
            get_text("screenshot.process_error", user_id=user_id, error=str(e)),
            parse_mode="HTML"
        )

# Hàm gửi video mà không đợi kết quả - chạy trong task riêng biệt
async def send_video_without_waiting(bot, chat_id, file_path, filename):
    """Gửi video mà không đợi kết quả - tránh timeout"""
    try:
        # Kiểm tra file có tồn tại không
        if not os.path.exists(file_path):
            logger.error(f"File không tồn tại: {file_path}")
            return
            
        # Gửi file với tham số read_timeout cao hơn
        with open(file_path, 'rb') as file:
            await bot.send_document(
                chat_id=chat_id,
                document=file,
                filename=filename,
                caption="<b>🎬 Video ghi màn hình của bạn.</b>",
                parse_mode="HTML",
                read_timeout=120,  # 2 phút timeout
                write_timeout=120,
                connect_timeout=60,
                pool_timeout=120
            )
        
        # Xóa file sau khi gửi
        try:
            os.remove(file_path)
            logger.info(f"Đã xóa file tạm: {file_path}")
        except Exception as e:
            logger.error(f"Lỗi khi xóa file: {e}")
            
    except Exception as e:
        logger.error(f"Lỗi khi gửi video (trong task riêng): {e}")
        # Không gọi API để gửi thông báo lỗi - tránh lỗi callback

# Xử lý lệnh /download_file
async def download_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tải file từ máy tính và gửi về Telegram"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
    
    user_id = update.effective_user.id
        
    if not context.args:
        await update.message.reply_text(
            get_text("file.download_help", user_id=user_id),
            parse_mode="HTML"
        )
        return

    # Lấy và lưu đường dẫn file vào context.user_data
    file_path = " ".join(context.args).strip()
    context.user_data["file_path"] = file_path

    # Kiểm tra file có tồn tại hay không
    if os.path.isfile(file_path):
        # Thông báo đang chuẩn bị
        status_message = await update.message.reply_text(
            get_text("file.path_valid", user_id=user_id, path=file_path),
            parse_mode="HTML"
        )
        
        try:
            # Kiểm tra kích thước file để đảm bảo không vượt quá giới hạn Telegram (50MB)
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # Kích thước MB
            if file_size > 50:
                await status_message.edit_text(
                    get_text("file.file_too_large", user_id=user_id, size=file_size),
                    parse_mode="HTML"
                )
                return
            
            # Cập nhật thông báo
            await status_message.edit_text(
                get_text("file.sending_file", user_id=user_id, size=file_size),
                parse_mode="HTML"
            )
            
            # Gửi file qua Telegram
            with open(file_path, 'rb') as file:
                message = await context.bot.send_document(
                    chat_id=update.effective_chat.id, 
                    document=file,
                    read_timeout=120,  # 2 phút timeout
                    write_timeout=120,
                    connect_timeout=60,
                    pool_timeout=120
                )
                
            # Kiểm tra xem file có được gửi thành công không
            if message:
                await status_message.edit_text(
                    get_text("file.send_success", user_id=user_id, path=file_path),
                    parse_mode="HTML"
                )
            else:
                await status_message.edit_text(
                    get_text("file.send_no_confirm", user_id=user_id),
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Lỗi khi gửi file {file_path}: {e}")
            # Đảm bảo thông báo lỗi an toàn cho HTML
            error_msg = str(e)
            safe_error = error_msg.replace("<", "&lt;").replace(">", "&gt;")
            await status_message.edit_text(
                get_text("file.send_error", user_id=user_id, error=safe_error),
                parse_mode="HTML"
            )
    else:
        await update.message.reply_text(
            get_text("file.file_not_found", user_id=user_id, path=file_path),
            parse_mode="HTML"
        )

# Yêu cầu gửi file
async def upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hiển thị hướng dẫn tải file lên máy tính"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
    
    user_id = update.effective_user.id
        
    await update.message.reply_text(
        get_text("file.upload_instruction", user_id=user_id, folder=UPLOAD_FOLDER),
        parse_mode="HTML"
    )

# Xử lý khi người dùng gửi file
async def upload_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý khi người dùng gửi file qua Telegram"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
    
    user_id = update.effective_user.id
    message = update.message

    # Ưu tiên lấy file tài liệu, nếu không thì kiểm tra ảnh hoặc video
    file = message.document or (message.photo[-1] if message.photo else None) or message.video

    if file:
        # Thông báo đang xử lý
        status_message = await update.message.reply_text(
            get_text("file.receiving_file", user_id=user_id),
            parse_mode="HTML"
        )
        
        try:
            # Lấy tên file, nếu không có, tạo tên file với đuôi mặc định
            if hasattr(file, "file_name") and file.file_name:
                file_name = file.file_name
            else:
                # Tạo tên file dựa trên loại
                if message.photo:
                    file_name = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                elif message.video:
                    file_name = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                else:
                    file_name = f"file_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    
            # Thêm cơ chế xử lý tên file trùng lặp
            original_name = file_name
            counter = 1
            while os.path.exists(os.path.join(UPLOAD_FOLDER, file_name)):
                name, ext = os.path.splitext(original_name)
                file_name = f"{name}_{counter}{ext}"
                counter += 1
                
            file_path = os.path.join(UPLOAD_FOLDER, file_name)
            
            # Cập nhật thông báo
            await status_message.edit_text(
                get_text("file.downloading", user_id=user_id),
                parse_mode="HTML"
            )

            # Tải file về máy
            new_file = await file.get_file()
            await new_file.download_to_drive(file_path)

            # Kiểm tra xem file có tải về thành công không
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path) / 1024  # Kích thước KB
                
                if file_size < 1024:
                    size_str = f"{file_size:.2f} KB"
                else:
                    size_str = f"{file_size/1024:.2f} MB"
                    
                await status_message.edit_text(
                    get_text("file.upload_success", user_id=user_id, filename=file_name, size=size_str, folder=UPLOAD_FOLDER),
                    parse_mode="HTML"
                )
            else:
                await status_message.edit_text(
                    get_text("file.upload_failed", user_id=user_id, filename=file_name),
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Lỗi khi tải file: {e}")
            # Đảm bảo thông báo lỗi an toàn cho HTML
            error_msg = str(e)
            safe_error = error_msg.replace("<", "&lt;").replace(">", "&gt;")
            await status_message.edit_text(
                get_text("file.upload_error", user_id=user_id, error=safe_error),
                parse_mode="HTML"
            )
    else:
        await update.message.reply_text(
            get_text("file.no_valid_file", user_id=user_id),
            parse_mode="HTML"
        )

async def deletefile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xóa file trên máy tính"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
    
    user_id = update.effective_user.id
        
    # Kiểm tra người dùng có nhập đường dẫn file không
    if not context.args:
        await update.message.reply_text(
            get_text("file.delete_help", user_id=user_id),
            parse_mode="HTML"
        )
        return

    # Lấy đường dẫn file từ tin nhắn
    file_path = " ".join(context.args).strip()
    
    # Kiểm tra tính hợp lệ của đường dẫn
    if not os.path.exists(file_path):
        await update.message.reply_text(
            get_text("file.path_not_found", user_id=user_id, path=file_path),
            parse_mode="HTML"
        )
        return
        
    # Kiểm tra xem là file hay thư mục
    if os.path.isfile(file_path):
        try:
            # Xóa file
            os.remove(file_path)
            await update.message.reply_text(
                get_text("file.delete_success", user_id=user_id, path=file_path),
                parse_mode="HTML"
            )
        except PermissionError:
            await update.message.reply_text(
                get_text("file.permission_error", user_id=user_id, path=file_path),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Lỗi khi xóa file {file_path}: {e}")
            # Đảm bảo thông báo lỗi an toàn cho HTML
            error_msg = str(e)
            safe_error = error_msg.replace("<", "&lt;").replace(">", "&gt;")
            await update.message.reply_text(
                get_text("file.delete_error", user_id=user_id, error=safe_error),
                parse_mode="HTML"
            )
    elif os.path.isdir(file_path):
        # Không cho phép xóa thư mục để tránh nguy hiểm
        await update.message.reply_text(
            get_text("file.is_directory", user_id=user_id, path=file_path),
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            get_text("file.invalid_path", user_id=user_id, path=file_path),
            parse_mode="HTML"
        )

# LỆNH TRUY VẤN THÔNG TIN HỆ THỐNG

# Ghi kết quả vào file và gửi file
async def run_command_to_file(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str, file_name: str, encoding='utf-8'):
    """Chạy lệnh CMD và ghi kết quả vào file, sau đó gửi file qua Telegram"""
    try:
        user_id = update.effective_user.id
        
        # Cập nhật tên file với timestamp để tránh trùng lặp
        time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_path = os.path.join(UPLOAD_FOLDER, f"{time_str}_{file_name}")
        
        # Thông báo đang xử lý
        wait_message = await update.message.reply_text(
            get_text("system_info.running_command", user_id=user_id, command=command),
            parse_mode="HTML"
        )
        
        try:
            # Chạy lệnh với timeout để tránh treo
            result = ""
            
            # Điều chỉnh lệnh dựa trên hệ điều hành
            if platform.system() == "Windows":
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True
                )
            else:
                # Với Linux/Mac, cần điều chỉnh lệnh đặc thù cho mỗi trường hợp
                if command == "tasklist":
                    command = "ps aux"
                elif command == "systeminfo":
                    command = "uname -a && lsb_release -a && cat /proc/cpuinfo"
                elif command.startswith("ipconfig"):
                    command = command.replace("ipconfig", "ifconfig")
                
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True
                )
            
            # Đặt timeout 30 giây
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30.0)
                if stdout:
                    result += stdout.decode(encoding, errors='replace')
                if stderr:
                    result += "\nStderr:\n" + stderr.decode(encoding, errors='replace')
            except asyncio.TimeoutError:
                process.terminate()
                result = "Lệnh thực thi quá thời gian (30 giây). Đã hủy."
        
        except Exception as e:
            logger.error(f"Lỗi khi thực thi lệnh {command}: {e}")
            result = f"Lỗi khi thực thi lệnh: {str(e)}"
        
        # Nếu không có kết quả, trả về thông báo
        if not result.strip():
            await wait_message.edit_text(
                get_text("system_info.no_result", user_id=user_id),
                parse_mode="HTML"
            )
            return
        
        # Ghi kết quả vào file
        with open(file_path, 'w', encoding=encoding) as file:
            file.write(result)

        # Kiểm tra kích thước file
        file_size = os.path.getsize(file_path) / 1024  # KB
        
        # Gửi thông báo kích thước file
        await wait_message.edit_text(
            get_text("system_info.command_success", user_id=user_id, size=file_size),
            parse_mode="HTML"
        )
        
        # Gửi file qua Telegram
        with open(file_path, 'rb') as file:
            await context.bot.send_document(chat_id=update.effective_chat.id, document=file)

        # Xóa file sau khi gửi
        try:
            os.remove(file_path)
        except Exception as e:
            logger.error(f"Không thể xóa file tạm {file_path}: {e}")
    except Exception as e:
        logger.error(f"Lỗi khi chạy lệnh và tạo file: {e}")
        # Đảm bảo thông báo lỗi an toàn cho HTML
        error_msg = str(e)
        safe_error = error_msg.replace("<", "&lt;").replace(">", "&gt;")
        await update.message.reply_text(
            get_text("system_info.command_error", user_id=user_id, error=safe_error),
            parse_mode="HTML"
        )

# Lệnh thông tin tiến trình
async def tasklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hiển thị danh sách các tiến trình đang chạy"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
        
    await run_command_to_file(update, context, "tasklist", "tasklist_output.txt")

# Lệnh thông tin hệ thống
async def systeminfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hiển thị thông tin hệ thống"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
        
    await run_command_to_file(update, context, "systeminfo", "systeminfo_output.txt")

# Lệnh cấu hình mạng
async def ipconfig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hiển thị thông tin cấu hình mạng"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
        
    # Chọn lệnh phù hợp với hệ điều hành
    if platform.system() == "Windows":
        command = "ipconfig /all"
    else:  # Linux/Mac
        command = "ifconfig -a"
        
    await run_command_to_file(update, context, command, "ipconfig_output.txt")

# Lệnh giải phóng IP
async def release(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Giải phóng địa chỉ IP"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
    
    user_id = update.effective_user.id
        
    # Kiểm tra nếu đang chạy trên Windows
    if platform.system() != "Windows":
        await update.message.reply_text(
            get_text("system_info.windows_only", user_id=user_id),
            parse_mode="HTML"
        )
        return
        
    await run_command_to_file(update, context, "ipconfig /release", "release_output.txt")

# Lệnh yêu cầu IP mới
async def renew(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yêu cầu địa chỉ IP mới"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
        
    user_id = update.effective_user.id
        
    # Kiểm tra nếu đang chạy trên Windows
    if platform.system() != "Windows":
        await update.message.reply_text(
            get_text("system_info.windows_only", user_id=user_id),
            parse_mode="HTML"
        )
        return
        
    await run_command_to_file(update, context, "ipconfig /renew", "renew_output.txt")

# Lệnh danh sách người dùng
async def netuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hiển thị danh sách người dùng trên máy tính"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
        
    # Chọn lệnh phù hợp với hệ điều hành
    if platform.system() == "Windows":
        command = "net user"
    else:  # Linux/Mac
        command = "cat /etc/passwd | cut -d: -f1"
        
    await run_command_to_file(update, context, command, "netuser_output.txt")

# Lệnh tên người dùng hiện tại
async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hiển thị tên tài khoản đang đăng nhập"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
        
    await run_command_to_file(update, context, "whoami", "whoami_output.txt")

# Lệnh tên máy tính
async def hostname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hiển thị tên máy tính"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
        
    await run_command_to_file(update, context, "hostname", "hostname_output.txt")

# CHỨC NĂNG MENU & THÔNG TIN

# Lệnh introduce
async def introduce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hiển thị thông tin giới thiệu về tác giả"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
    
    user_id = update.effective_user.id
    
    # Lấy nội dung giới thiệu từ bản dịch
    await update.message.reply_text(
        get_text("messages.introduce_content", user_id=user_id),
        parse_mode="HTML"
    )

# Lệnh menu
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hiển thị danh sách các lệnh theo nhóm"""
    # Kiểm tra quyền người dùng
    if not await check_user_permission(update):
        return
    
    user_id = update.effective_user.id
    menu_text = f"{get_text('messages.menu_title', user_id=user_id)}\n{get_text('messages.author', user_id=user_id)}\n\n"
    
    # Lấy danh sách lệnh theo ngôn ngữ người dùng
    command_groups = get_command_groups(user_id)
    
    # Tạo danh sách lệnh theo từng nhóm
    for group_key, group_info in command_groups.items():
        group_title = group_info["title"]
        commands = group_info["commands"]
        
        # Định dạng lệnh trong nhóm
        command_list = "\n".join([
            f"<b>🔻</b> <code>{command}</code> <b>➡️</b> {desc}" for command, desc in commands.items()
        ])
        
        # Thêm nhóm vào menu
        menu_text += f"<b>{group_title}</b>\n{command_list}\n\n"
    
    await update.message.reply_text(menu_text, parse_mode="HTML")

# Đặt mô tả lệnh cho bot
async def set_command_suggestions(context: ContextTypes.DEFAULT_TYPE):
    """Đặt mô tả lệnh để hiển thị trong menu chat Telegram"""
    # Sử dụng ngôn ngữ mặc định cho các lệnh ban đầu
    commands = [BotCommand(command, desc) for command, desc in get_commands(None).items()]
    await context.bot.set_my_commands(commands)

# KHỞI CHẠY BOT

async def main():
    """Hàm chính để khởi chạy bot"""
    # Kiểm tra file .env có tồn tại không
    if not os.path.exists('.env'):
        # Tạo file .env với token mặc định
        with open('.env', 'w') as f:
            f.write(f"TOKEN=REPLACE-YOUR-TOKEN\n")
            f.write(f"ALLOWED_USERS=REPLACE-YOUR-ID-CHAT\n")
        logger.info("Đã tạo file .env với token mặc định. Vui lòng kiểm tra và cập nhật thông tin nếu cần!")
    
    # Tải cấu hình ngôn ngữ nếu có
    load_language_config()
    
    # Kiểm tra token có hợp lệ không
    if not BOT_TOKEN:
        logger.error("CẢNH BÁO: Không tìm thấy TOKEN bot trong file .env! Hãy kiểm tra lại.")
        return
    
    # Khởi tạo bot
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Gắn các lệnh giới thiệu và trợ giúp
    app.add_handler(CommandHandler("introduce", introduce))
    app.add_handler(CommandHandler("menu", menu))
    
    # Gắn lệnh set_language
    app.add_handler(CommandHandler("set_language", set_language))
    app.add_handler(CallbackQueryHandler(handle_language_selection, pattern=r"^lang_"))
    
    # Gắn các lệnh điều khiển hệ thống
    app.add_handler(CommandHandler("shutdown", shutdown))
    app.add_handler(CommandHandler("restart", restart))
    app.add_handler(CommandHandler("sleep", sleep))
    app.add_handler(CommandHandler("cancel", cancel))
    
    # Gắn các lệnh hình ảnh
    app.add_handler(CommandHandler("screen_shot", screen_shot))
    app.add_handler(CommandHandler("record_video", record_video))
    app.add_handler(CallbackQueryHandler(handle_stop_recording, pattern="^stop_recording$"))
    
    # Gắn các lệnh quản lý file
    app.add_handler(CommandHandler("upload_file", upload_file))
    app.add_handler(CommandHandler("download_file", download_file))
    app.add_handler(CommandHandler("deletefile", deletefile))
    app.add_handler(MessageHandler(filters.ATTACHMENT, upload_file_handler))
    
    # Gắn các lệnh thông tin hệ thống
    app.add_handler(CommandHandler("tasklist", tasklist))
    app.add_handler(CommandHandler("systeminfo", systeminfo))
    app.add_handler(CommandHandler("ipconfig", ipconfig))
    app.add_handler(CommandHandler("release", release))
    app.add_handler(CommandHandler("renew", renew))
    app.add_handler(CommandHandler("netuser", netuser))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("hostname", hostname))
    
    # Gắn các lệnh trình duyệt
    app.add_handler(CommandHandler("playvideo", play_video))
    app.add_handler(CommandHandler("openweb", open_web))
    app.add_handler(CommandHandler("setbrowser", set_browser))
    
    # Gắn các lệnh tiện ích
    app.add_handler(CommandHandler("keyboard_emulator", keyboard_emulator))
    
    # Thêm lệnh touchpad ảo
    app.add_handler(CommandHandler("mouse_virtual_system", mouse_virtual_system))
    app.add_handler(CommandHandler("volume_virtual_system", volume_virtual_system))
    app.add_handler(CommandHandler("stop_touchpad", stop_touchpad_command))
    app.add_handler(CallbackQueryHandler(refresh_touchpad, pattern="^refresh_touchpad$"))
    app.add_handler(CallbackQueryHandler(refresh_volume_touchpad, pattern="^refresh_volume_touchpad$"))
    
    # Xử lý tin nhắn văn bản
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_key_press))
    
    # Xử lý các callback từ nút
    app.add_handler(CallbackQueryHandler(handle_browser_selection, pattern="^browser_"))
    app.add_handler(CallbackQueryHandler(video_controls, pattern="^(play_pause|rewind|forward|close_browser)$"))
    app.add_handler(CallbackQueryHandler(web_controls, pattern="^(reload_page|back_page|forward_page)$"))
    app.add_handler(CallbackQueryHandler(confirm_action, pattern="^confirm$"))
    app.add_handler(CallbackQueryHandler(cancel_action, pattern="^cancel_action$"))

    # Thiết lập các gợi ý lệnh
    app.post_init = set_command_suggestions
    
    # Hiển thị thông tin hệ thống
    logger.info(f"Hệ điều hành: {platform.system()} {platform.release()}")
    logger.info(f"Thư mục lưu file tải về: {UPLOAD_FOLDER}")
    
    # Nếu là Windows, kiểm tra trình duyệt có sẵn
    if platform.system() == "Windows":
        available_browsers = []
        for browser, path in BROWSER_PATHS.items():
            if os.path.exists(path):
                available_browsers.append(browser)
        
        if available_browsers:
            logger.info(f"Các trình duyệt khả dụng: {', '.join(available_browsers)}")
        else:
            logger.warning("Không tìm thấy trình duyệt nào trên hệ thống!")
    
    # Đăng ký tín hiệu để dọn dẹp khi thoát
    def cleanup():
        logger.info("Đang dọn dẹp trước khi thoát...")
        # Dừng Ngrok nếu đang chạy
        if 'ngrok_tunnel' in globals() and ngrok_tunnel:
            logger.info(f"Đóng kết nối Ngrok: {ngrok_tunnel.public_url}")
            try:
                ngrok.disconnect(ngrok_tunnel.public_url)
            except Exception as e:
                logger.error(f"Lỗi khi đóng kết nối Ngrok: {e}")
            
        # Dừng Flask server nếu đang chạy
        logger.info("Flask server sẽ tự động dừng khi chương trình kết thúc")
        
        # Lưu cấu hình ngôn ngữ
        save_language_config()
    
    # Đăng ký hàm dọn dẹp với atexit
    import atexit
    atexit.register(cleanup)
    
    # Chạy bot
    logger.info("Bot đang khởi động...")
    app.run_polling()

if __name__ == "__main__":
    # Chạy chương trình chính
    asyncio.run(main())