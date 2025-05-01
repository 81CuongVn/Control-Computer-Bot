from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from translations import get_text

def create_confirmation_keyboard(user_id):
    """Tạo bàn phím xác nhận với các nút theo ngôn ngữ người dùng"""
    keyboard = [
        [
            InlineKeyboardButton(get_text("buttons.confirm", user_id=user_id), callback_data="confirm"),
            InlineKeyboardButton(get_text("buttons.cancel", user_id=user_id), callback_data="cancel_action")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_stop_recording_keyboard(user_id):
    """Tạo bàn phím với nút dừng quay video"""
    keyboard = [
        [InlineKeyboardButton(get_text("buttons.stop_recording", user_id=user_id), callback_data="stop_recording")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_refresh_keyboard(user_id, callback_data="refresh_touchpad"):
    """Tạo bàn phím với nút làm mới kết nối"""
    keyboard = [
        [InlineKeyboardButton(get_text("buttons.refresh_connection", user_id=user_id), callback_data=callback_data)]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_browser_selection_keyboard(user_id, available_browsers):
    """Tạo bàn phím chọn trình duyệt"""
    keyboard = []
    browser_row = []
    
    for i, browser_name in enumerate(available_browsers.keys()):
        browser_row.append(InlineKeyboardButton(
            browser_name.capitalize(), 
            callback_data=f"browser_{browser_name}"
        ))
        
        # Mỗi hàng chứa 2 nút
        if len(browser_row) == 2 or i == len(available_browsers) - 1:
            keyboard.append(browser_row)
            browser_row = []
    
    return InlineKeyboardMarkup(keyboard)

def create_video_controls_keyboard(user_id):
    """Tạo bàn phím điều khiển video"""
    keyboard = [
        [
            InlineKeyboardButton(get_text("buttons.play_pause", user_id=user_id), callback_data="play_pause"),
            InlineKeyboardButton(get_text("buttons.rewind", user_id=user_id), callback_data="rewind")
        ],
        [
            InlineKeyboardButton(get_text("buttons.forward", user_id=user_id), callback_data="forward"),
            InlineKeyboardButton(get_text("buttons.close_browser", user_id=user_id), callback_data="close_browser")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_web_controls_keyboard(user_id):
    """Tạo bàn phím điều khiển trình duyệt web"""
    keyboard = [
        [
            InlineKeyboardButton(get_text("buttons.reload_page", user_id=user_id), callback_data="reload_page"),
            InlineKeyboardButton(get_text("buttons.back_page", user_id=user_id), callback_data="back_page")
        ],
        [
            InlineKeyboardButton(get_text("buttons.forward_page", user_id=user_id), callback_data="forward_page"),
            InlineKeyboardButton(get_text("buttons.close_browser", user_id=user_id), callback_data="close_browser")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_language_keyboard():
    """Tạo bàn phím chọn ngôn ngữ"""
    keyboard = [
        [InlineKeyboardButton("🇻🇳 Tiếng Việt", callback_data="lang_vi")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
    ]
    return InlineKeyboardMarkup(keyboard)