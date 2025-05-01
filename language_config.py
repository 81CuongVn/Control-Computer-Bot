import os
import json
import logging

# Thiết lập logging cho file này
logger = logging.getLogger(__name__)

# Biến toàn cục cho đa ngôn ngữ
DEFAULT_LANGUAGE = "vi"  # Mặc định là tiếng Việt
USER_LANGUAGES = {}  # Dict lưu trữ ngôn ngữ đã chọn của từng người dùng

# Đường dẫn đến file cấu hình ngôn ngữ
CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
LANGUAGE_CONFIG_FILE = os.path.join(CONFIG_DIR, 'user_languages.json')

# Đảm bảo thư mục cấu hình tồn tại
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

# Tải cấu hình ngôn ngữ nếu có
def load_language_config():
    global USER_LANGUAGES
    if os.path.exists(LANGUAGE_CONFIG_FILE):
        try:
            with open(LANGUAGE_CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Chuyển đổi key từ string sang int
                USER_LANGUAGES = {int(k): v for k, v in data.items()}
                logger.info(f"Đã tải cấu hình ngôn ngữ cho {len(USER_LANGUAGES)} người dùng")
        except Exception as e:
            logger.error(f"Lỗi khi đọc file cấu hình ngôn ngữ: {e}")
            USER_LANGUAGES = {}

# Lưu cấu hình ngôn ngữ
def save_language_config():
    try:
        with open(LANGUAGE_CONFIG_FILE, 'w', encoding='utf-8') as f:
            # Chuyển đổi key từ int sang string cho JSON
            json_data = {str(k): v for k, v in USER_LANGUAGES.items()}
            json.dump(json_data, f, ensure_ascii=False, indent=4)
            logger.info(f"Đã lưu cấu hình ngôn ngữ cho {len(USER_LANGUAGES)} người dùng")
    except Exception as e:
        logger.error(f"Lỗi khi lưu file cấu hình ngôn ngữ: {e}")

# Lấy ngôn ngữ hiện tại của người dùng
def get_user_language(user_id):
    if user_id in USER_LANGUAGES:
        return USER_LANGUAGES[user_id]
    return DEFAULT_LANGUAGE

# Đặt ngôn ngữ cho người dùng
def set_user_language(user_id, language):
    USER_LANGUAGES[user_id] = language
    save_language_config()