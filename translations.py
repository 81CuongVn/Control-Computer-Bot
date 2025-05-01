from language_config import get_user_language
import logging

# Thiết lập logging
logger = logging.getLogger(__name__)

# Bộ dịch đa ngôn ngữ
TRANSLATIONS = {
    "vi": {  # Tiếng Việt
        "command_groups": {
            "intro": {
                "title": "⚡️ GIỚI THIỆU",
                "commands": {
                    "/introduce": "Giới thiệu về tôi."
                }
            },
            "system": {
                "title": "⚡️ ĐIỀU KHIỂN HỆ THỐNG",
                "commands": {
                    "/shutdown": "Lệnh tắt máy.",
                    "/sleep": "Lệnh vào chế độ ngủ.",
                    "/restart": "Lệnh khởi động máy.",
                    "/cancel": "Huỷ toàn bộ các lệnh."
                }
            },
            "image": {
                "title": "⚡️ LỆNH HÌNH ẢNH",
                "commands": {
                    "/screen_shot": "Chụp ảnh màn hình và gửi về máy.",
                    "/record_video": "Quay video màn hình và gửi về máy."
                }
            },
            "file": {
                "title": "⚡️ QUẢN LÝ FILE",
                "commands": {
                    "/upload_file": "Người dùng gửi file để tải lên máy.",
                    "/download_file": "Người dùng nhập đường dẫn để tải về.",
                    "/deletefile": "Người dùng nhập đường dẫn để xoá file."
                }
            },
            "info": {
                "title": "⚡️ THÔNG TIN HỆ THỐNG",
                "commands": {
                    "/tasklist": "Danh sách các tiến trình đang chạy.",
                    "/systeminfo": "Thông tin hệ thống.",
                    "/netuser": "Danh sách người dùng trên máy tính.",
                    "/whoami": "Tên tài khoản đang đăng nhập.",
                    "/hostname": "Hiển thị tên máy tính."
                }
            },
            "network": {
                "title": "⚡️ MẠNG",
                "commands": {
                    "/ipconfig": "Thông tin cấu hình mạng.",
                    "/release": "Giải phóng địa chỉ IP hiện tại.",
                    "/renew": "Gia hạn địa chỉ IP mới."
                }
            },
            "browser": {
                "title": "⚡️ TRÌNH DUYỆT",
                "commands": {
                    "/playvideo": "Phát video YouTube từ link.",
                    "/openweb": "Mở các trang web.",
                    "/setbrowser": "Chọn trình duyệt mặc định (chrome, brave, edge, opera)."
                }
            },
            "utility": {
                "title": "⚡️ TIỆN ÍCH",
                "commands": {
                    "/mouse_virtual_system": "Điều khiển chuột với touchpad ảo.",
                    "/volume_virtual_system": "Điều khiển âm lượng với touchpad ảo.",
                    "/keyboard_emulator": "Điều khiển bàn phím ảo.",
                    "/stop_touchpad": "Dừng touchpad đang chạy.",
                    "/set_language": "Thay đổi ngôn ngữ hiển thị."
                }
            },
            "help": {
                "title": "⚡️ TRỢ GIÚP",
                "commands": {
                    "/menu": "Hiển thị danh sách các lệnh."
                }
            }
        },
        "messages": {
            "permission_denied": "⚠️ Bạn không có quyền sử dụng bot này!\n\nBot này chỉ phục vụ cho người dùng được ủy quyền.",
            "no_permission_log": "Người dùng không được phép truy cập: ID {user_id}, Tên: {user_name}",
            "menu_title": "📋 DANH SÁCH CÁC LỆNH",
            "author": "📌 Author: LePhiAnhDev",
            "set_language_title": "🌐 Chọn ngôn ngữ hiển thị cho bot:",
            "current_language": "Ngôn ngữ hiện tại: Tiếng Việt",
            "already_using_language": "✅ Bạn đang sử dụng Tiếng Việt, không có gì thay đổi.",
            "language_changed": "✅ Đã chuyển sang Tiếng Việt.",
            "introduce_content": "<b>👨‍💻 DEVELOPER | LÊ PHI ANH</b>\n\n<strong>Bất cứ dự án hay công việc nào bạn muốn hợp tác, mình luôn sẵn sàng. Hãy liên hệ ngay để cùng nhau tạo ra những giá trị tốt đẹp!</strong>\n\n<b>📩 CONTACT FOR WORK:</b>\n• Discord: <code>LePhiAnhDev</code>\n• Telegram: <a href='https://t.me/lephianh386ht'>@lephianh386ht</a>\n• GitHub: <a href='https://github.com/LePhiAnhDev'>LePhiAnhDev</a>\n• My Website: <a href='https://lephianh.id.vn/'>lephianh.id.vn</a>\n\n<b>🌟 DONATE ME:</b>\n• 💳 <b>Bank:</b> <code>1039506134</code> | LE PHI ANH | Vietcombank\n• 🏦 <b>MoMo:</b> <code>0971390849</code> | LE PHI ANH\n• 💰 <b>Metamask:</b> <code>0x928F8c5443b13f71a4d7094E8bD2E74c86127243</code>\n\nNhấn <b>/menu</b> để xem danh sách các lệnh"
        },
        "touchpad": {
            "missing_libs": "<b>❌ Tính năng này yêu cầu Flask và pyngrok.</b>\n<b>Vui lòng cài đặt thư viện bằng lệnh:</b>\n<code>pip install flask pyngrok</code>",
            "mouse_init_error": "<b>❌ Không thể khởi tạo bộ điều khiển chuột.</b>\n<b>Vui lòng kiểm tra quyền truy cập hoặc chạy với quyền admin.</b>",
            "already_running": "<b>✅ Touchpad chuột đã đang chạy!</b>\n\n<b>🔗 Truy cập URL sau trên điện thoại của bạn:</b>\n<code>{url}</code>\n\n<b>📱 Để điều khiển chuột:</b>\n• Chạm và kéo trên màn hình touchpad để di chuyển chuột\n• Nhấn nút để thực hiện các thao tác chuột\n• Chế độ cuộn cho phép bạn cuộn trang lên/xuống\n\n<b>⚠️ Kết nối này sẽ hết hạn sau khoảng 2 giờ</b>",
            "stopping_current": "<b>🔄 Đang dừng {type} touchpad đang chạy...</b>",
            "cannot_stop": "<b>❌ Không thể dừng touchpad hiện tại:</b> {message}",
            "stopped_starting_new": "<b>✅ Đã dừng {message}</b>\n<b>🔄 Đang khởi động mouse touchpad mới...</b>",
            "starting": "<b>🔄 Đang khởi động touchpad ảo qua Ngrok, vui lòng đợi...</b>",
            "flask_started": "<b>✅ Đã khởi động máy chủ web Flask thành công.</b>\n<b>🔄 Đang kết nối Ngrok...</b>",
            "ngrok_error": "<b>❌ Không thể khởi động Ngrok.</b>\n\n<b>Vui lòng kiểm tra kết nối mạng và cài đặt Ngrok.</b>",
            "ready": "<b>✅ Touchpad ảo đã sẵn sàng!</b>\n\n<b>🔗 Truy cập URL sau trên điện thoại của bạn:</b>\n{url}\n\n<b>📱 Để điều khiển chuột:</b>\n• Chạm và kéo trên màn hình touchpad để di chuyển chuột\n• Nhấn nút để thực hiện các thao tác chuột\n• Chế độ cuộn cho phép bạn cuộn trang lên/xuống\n\n<b>⚠️ Kết nối này sẽ hết hạn sau khoảng 2 giờ</b>\n<b>💡 Sử dụng /stop_touchpad để dừng khi không cần nữa</b>",
            "error_init": "<b>❌ Có lỗi xảy ra khi khởi tạo touchpad ảo:</b> {error}",
            "error_ngrok": "<b>❌ Lỗi khi khởi động Ngrok:</b> {error}\n\n<b>Vui lòng kiểm tra cài đặt Ngrok và thử lại.</b>",
            "none_running": "<b>❌ Không có touchpad nào đang hoạt động.</b>\n<b>Hãy khởi động touchpad trước bằng /mouse_virtual_system hoặc /volume_virtual_system</b>",
            "refreshing": "<b>🔄 Đang làm mới kết nối Ngrok, vui lòng đợi...</b>",
            "refresh_error": "<b>❌ Không thể khởi động lại Ngrok.</b>\n\n<b>Vui lòng kiểm tra kết nối mạng và cài đặt Ngrok.</b>",
            "invalid_type": "<b>❌ Loại touchpad không hợp lệ.</b>",
            "refresh_success": "<b>✅ Đã làm mới kết nối thành công!</b>\n\n<b>🔗 Truy cập URL mới trên điện thoại của bạn:</b>\n<code>{url}{endpoint}</code>\n\n<b>📱 Hướng dẫn sử dụng:</b>\n{action_info}\n\n<b>⚠️ Kết nối này sẽ hết hạn sau khoảng 2 giờ</b>\n<b>💡 Sử dụng /stop_touchpad để dừng khi không cần nữa</b>",
            "refresh_error_general": "<b>❌ Có lỗi khi làm mới kết nối:</b> {error}",
            "volume_already_running": "<b>✅ Touchpad âm lượng đã đang chạy!</b>\n\n<b>🔗 Truy cập URL sau trên điện thoại của bạn:</b>\n<code>{url}/volume</code>\n\n<b>📱 Hướng dẫn sử dụng:</b>\n• Kéo thanh trượt sang trái/phải để điều chỉnh âm lượng\n• Nhấn các nút để nhanh chóng đặt mức âm lượng cụ thể\n\n<b>⚠️ Kết nối này sẽ hết hạn sau khoảng 2 giờ</b>",
            "pycaw_error": "<b>❌ Không thể điều khiển âm lượng vì thư viện pycaw không khả dụng hoặc bạn đang sử dụng hệ điều hành không phải Windows.</b> <b>Vui lòng kiểm tra cài đặt thư viện và hệ điều hành.</b>",
            "stopped_volume_new": "<b>✅ Đã dừng {message}</b>\n<b>🔄 Đang khởi động volume touchpad mới...</b>",
            "starting_volume": "<b>🔄 Đang khởi động touchpad âm lượng qua Ngrok, vui lòng đợi...</b>",
            "volume_ready": "<b>✅ Touchpad điều chỉnh âm lượng đã sẵn sàng!</b>\n\n<b>🔗 Truy cập URL sau trên điện thoại của bạn:</b>\n{url}/volume\n\n<b>📱 Hướng dẫn sử dụng:</b>\n• Kéo thanh trượt sang trái/phải để điều chỉnh âm lượng\n• Nhấn các nút để nhanh chóng đặt mức âm lượng cụ thể\n\n<b>⚠️ Kết nối này sẽ hết hạn sau khoảng 2 giờ</b>\n<b>💡 Sử dụng /stop_touchpad để dừng khi không cần nữa</b>",
            "volume_error_init": "<b>❌ Có lỗi xảy ra khi khởi tạo touchpad âm lượng:</b> {error}",
            "no_volume_touchpad": "<b>❌ Không có touchpad âm lượng nào đang hoạt động.</b>\n<b>Hãy khởi động touchpad trước bằng /volume_virtual_system</b>",
            "none_running_stop": "<b>❌ Không có touchpad nào đang chạy.</b>",
            "stopping": "<b>🔄 Đang dừng {type} touchpad...</b>",
            "stop_success": "<b>✅ Đã dừng {message} thành công.</b>",
            "stop_error": "<b>❌ Không thể dừng touchpad: {message}</b>",
            "mouse_instruction": "• Chạm và kéo trên màn hình touchpad để di chuyển chuột\n• Nhấn nút để thực hiện các thao tác chuột\n• Chế độ cuộn cho phép bạn cuộn trang lên/xuống",
            "volume_instruction": "• Kéo thanh trượt sang trái/phải để điều chỉnh âm lượng\n• Nhấn các nút để nhanh chóng đặt mức âm lượng cụ thể"
        },
        "keyboard": {
            "instruction": "<b>⌨️ Đây là bàn phím QWERTY mô phỏng. Nhấn /menu để quay lại.</b>",
            "key_pressed": "<b>✅ Đã nhấn phím:</b> <code>{key}</code>",
            "key_error": "<b>❌ Lỗi khi nhấn phím:</b> {error}"
        },
        "browser": {
            "setbrowser_help": "<b>⚠️ Hãy nhập URL website bạn muốn mở. Ví dụ:</b>\n<code>/openweb https://www.google.com</code>\n<b>hoặc</b>\n<code>/openweb google.com</code>",
            "no_browsers": "<b>❌ Không tìm thấy trình duyệt nào được cài đặt trên hệ thống.</b>",
            "current_browser": "<b>Trình duyệt hiện tại:</b> {browser}\n<b>Vui lòng chọn trình duyệt mặc định:</b>\n\n<i>Lưu ý: Microsoft Edge có thể gặp vấn đề và sẽ tự động chuyển sang trình duyệt khác nếu gặp lỗi. Nếu muốn dùng Edge, hãy chạy bot với quyền Admin và đóng tất cả cửa sổ Edge đang mở trước.</i>",
            "set_success": "<b>✅ Đã đặt {browser} làm trình duyệt mặc định.</b>",
            "edge_note": "\n\n<i>Lưu ý: Microsoft Edge có thể gặp vấn đề. Nếu gặp lỗi, bot sẽ tự động chuyển sang trình duyệt khác. Để tăng khả năng thành công, hãy chạy bot với quyền Admin và đóng các cửa sổ Edge đang mở.</i>",
            "browser_not_found": "<b>❌ Không tìm thấy trình duyệt {browser} tại: {path}</b>",
            "invalid_browser": "<b>❌ Trình duyệt không hợp lệ. Vui lòng chọn Chrome, Brave, Edge hoặc Opera.</b>",
            "youtube_link_help": "<b>⚠️ Hãy gửi một link YouTube kèm lệnh /playvideo [link].</b>",
            "invalid_youtube": "<b>❌ Link YouTube không hợp lệ. Vui lòng kiểm tra lại.</b>",
            "starting_browser": "<b>🔄 Đang khởi động trình duyệt {browser}...</b>",
            "browser_started": "<b>✅ Đã khởi động trình duyệt {browser} thành công.</b>",
            "browser_error": "<b>❌ Không thể khởi động trình duyệt:</b> {error}",
            "opening_video": "<b>🔄 Đang mở video bằng {browser}...</b>",
            "video_opened": "<b>✅ Đã mở video YouTube thành công trên {browser}.</b>",
            "video_not_found": "<b>⚠️ Không thể tìm thấy trình phát video. Trang đã được mở nhưng có thể không phải là video YouTube.</b>",
            "select_action": "<b>🎮 Chọn hành động:</b>",
            "url_error": "<b>❌ Không thể mở URL.</b> Kiểm tra kết nối mạng hoặc URL.",
            "general_error": "<b>❌ Có lỗi xảy ra:</b> {error}",
            "no_browser_open": "<b>❌ Không có trình duyệt nào đang mở.</b>",
            "play_pause": "<b>✅ Đã chuyển trạng thái phát / tạm dừng.</b>",
            "rewind": "<b>⏪ Đã tua lại 10 giây.</b>",
            "forward": "<b>⏩ Đã tua tới 10 giây.</b>",
            "browser_closed": "<b>✅ Đã đóng trình duyệt {browser}.</b>",
            "video_control_error": "<b>❌ Có lỗi xảy ra khi điều khiển video:</b> {error}",
            "opening_website": "<b>🔄 Đang mở trang web {url}...</b>",
            "website_opened": "<b>✅ Đã mở trang web {url} trong trình duyệt {browser}.</b>",
            "page_reloaded": "<b>🔄 Đã tải lại trang.</b>",
            "back_success": "<b>⬅️ Đã quay lại trang trước.</b>",
            "back_error": "<b>⚠️ Không có trang trước để quay lại.</b>",
            "forward_success": "<b>➡️ Đã tiến tới trang sau.</b>",
            "forward_error": "<b>⚠️ Không có trang sau để tiến tới.</b>",
            "web_control_error": "<b>❌ Có lỗi xảy ra khi điều khiển trình duyệt:</b> {error}"
        },
        "system": {
            "confirm_shutdown": "<b>⚠️ Bạn có chắc chắn muốn tắt máy tính không?</b>",
            "confirm_restart": "<b>⚠️ Bạn có chắc chắn muốn khởi động lại máy tính không?</b>",
            "confirm_sleep": "<b>⚠️ Bạn có chắc chắn muốn đưa máy tính vào chế độ ngủ không?</b>",
            "confirm_cancel": "<b>⚠️ Bạn có chắc chắn muốn hủy tất cả các lệnh tắt/khởi động không?</b>",
            "shutdown_progress": "<b>🔄 Máy sẽ tắt sau 3 giây.</b>",
            "restart_progress": "<b>🔄 Máy sẽ khởi động lại sau 3 giây.</b>",
            "cancel_progress": "<b>🔄 Đang hủy lệnh tắt/khởi động lại...</b>",
            "cancel_success": "<b>✅ Đã hủy toàn bộ lệnh tắt/khởi động lại.</b>",
            "cancel_none": "<b>ℹ️ Không có lệnh nào để hủy.</b>",
            "sleep_progress": "<b>🔄 Máy tính sẽ vào chế độ ngủ ngay bây giờ.</b>",
            "no_action": "<b>ℹ️ Không có hành động được thực hiện.</b>",
            "command_error": "<b>❌ Có lỗi xảy ra khi thực hiện lệnh:</b> {error}",
            "action_cancelled": "<b>❎ Hành động đã bị hủy.</b>"
        },
        "screenshot": {
            "taking": "<b>🔄 Đang chụp màn hình...</b>",
            "error": "<b>❌ Không thể chụp ảnh màn hình.</b>",
            "sending": "<b>🔄 Ảnh màn hình đã chụp, đang gửi...</b>",
            "saving_error": "<b>❌ Không thể lưu ảnh chụp màn hình.</b>",
            "size_error": "<b>⚠️ Ảnh quá lớn ({size} MB) vượt quá giới hạn Telegram (50MB).</b>",
            "sending_progress": "<b>✅ Ảnh chụp màn hình đang được gửi dưới dạng tệp, sẽ xuất hiện trong chat sau khi xử lý xong.</b>",
            "screenshot_error": "<b>❌ Có lỗi xảy ra khi chụp ảnh màn hình:</b> {error}",
            "already_recording": "<b>⚠️ Đang quay video rồi. Vui lòng dừng ghi hiện tại trước.</b>",
            "prepare_recording": "<b>🔄 Chuẩn bị quay video màn hình (tối đa 30 giây)...</b>",
            "start_error": "<b>❌ Không thể bắt đầu quay video màn hình.</b>",
            "recording_started": "<b>🎥 Đã bắt đầu quay video màn hình (tối đa 30 giây). Nhấn nút dưới đây để dừng và lưu video.</b>",
            "no_recording": "<b>❌ Không có quá trình ghi video nào đang diễn ra.</b>",
            "stopping_video": "<b>⏳ Đang dừng và xử lý video, vui lòng đợi...</b>",
            "video_not_found": "<b>❌ Không tìm thấy file video ghi màn hình.</b>",
            "size_too_large": "<b>❌ Video quá lớn ({size} MB) để gửi qua Telegram (giới hạn 50MB).</b> <b>Đã lưu tại:</b> <code>{path}</code>",
            "size_too_small": "<b>⚠️ Video có vẻ không hợp lệ (kích thước quá nhỏ: {size} MB).</b> <b>Vui lòng thử lại với thời gian ghi dài hơn.</b>",
            "sending_video": "<b>📤 Đang gửi video...</b>\n<b>(Tin nhắn này sẽ được cập nhật khi hoàn tất)</b>",
            "video_sent": "<b>✅ Video đang được gửi trong nền, sẽ xuất hiện trong chat sau khi xử lý xong.</b>\n<b>Kích thước:</b> {size} MB",
            "video_error": "<b>❌ Có lỗi khi gửi video:</b> {error}\n<b>Đã lưu tại:</b> <code>{path}</code>",
            "process_error": "<b>❌ Có lỗi xử lý video:</b> {error}"
        },
        "file": {
            "download_help": "<b>⚠️ Hãy nhập đường dẫn file bạn muốn tải về. Ví dụ:</b>\n<code>/download_file D:/example.txt</code>",
            "path_valid": "<b>✅ Đường dẫn hợp lệ. Đang chuẩn bị gửi file:</b> <code>{path}</code>",
            "file_too_large": "<b>❌ File quá lớn ({size} MB). Telegram chỉ cho phép gửi file tối đa 50MB.</b>",
            "sending_file": "<b>🔄 Đang gửi file ({size} MB)...</b>",
            "send_success": "<b>✅ File đã được gửi thành công:</b> <code>{path}</code>",
            "send_no_confirm": "<b>⚠️ Không nhận được xác nhận gửi file.</b>",
            "send_error": "<b>❌ Có lỗi xảy ra khi gửi file:</b> {error}",
            "file_not_found": "<b>❌ Không tìm thấy file tại đường dẫn:</b> <code>{path}</code>",
            "upload_instruction": "<b>📤 Hãy gửi file bạn muốn tải lên. File sẽ được lưu vào thư mục</b> <code>{folder}</code>",
            "receiving_file": "<b>🔄 Đang nhận file...</b>",
            "downloading": "<b>🔄 Đang tải file về máy tính...</b>",
            "upload_success": "<b>✅ File {filename} ({size}) đã được tải và lưu trong thư mục</b> <code>{folder}</code>",
            "upload_failed": "<b>❌ Không thể tải file {filename}.</b>",
            "upload_error": "<b>❌ Có lỗi xảy ra khi tải file:</b> {error}",
            "no_valid_file": "<b>❌ Không nhận được file hợp lệ. Vui lòng thử lại!</b>",
            "delete_help": "<b>⚠️ Hãy nhập đường dẫn file bạn muốn xoá. Ví dụ:</b>\n<code>/deletefile D:/example.txt</code>",
            "path_not_found": "<b>❌ Không tìm thấy file hoặc thư mục tại đường dẫn:</b> <code>{path}</code>",
            "delete_success": "<b>✅ File tại đường dẫn</b> <code>{path}</code> <b>đã được xóa thành công.</b>",
            "permission_error": "<b>❌ Không có quyền xóa file:</b> <code>{path}</code>. <b>File có thể đang được sử dụng bởi chương trình khác.</b>",
            "delete_error": "<b>❌ Có lỗi xảy ra khi xóa file:</b> {error}",
            "is_directory": "<b>⚠️ {path} là thư mục. Lệnh này chỉ xóa file, không xóa thư mục.</b>",
            "invalid_path": "<b>❓ Đường dẫn</b> <code>{path}</code> <b>không phải là file hoặc thư mục hợp lệ.</b>"
        },
        "system_info": {
            "running_command": "<b>🔄 Đang chạy lệnh</b> <code>'{command}'</code><b>...</b>",
            "no_result": "<b>⚠️ Lệnh không trả về kết quả hoặc có lỗi xảy ra.</b>",
            "command_success": "<b>✅ Đã chạy lệnh thành công. Kích thước file:</b> {size} KB.",
            "command_error": "<b>❌ Có lỗi xảy ra khi chạy lệnh:</b> {error}",
            "windows_only": "<b>❌ Lệnh này chỉ hỗ trợ trên Windows.</b>"
        },
        "buttons": {
            "confirm": "✅ Xác nhận",
            "cancel": "❎ Hủy",
            "stop_recording": "⏹️ Dừng quay",
            "refresh_connection": "🔄 Làm mới kết nối",
            "play_pause": "⏯ Phát / Tạm dừng",
            "rewind": "⏪ Tua lại 10s",
            "forward": "⏩ Tua tới 10s",
            "close_browser": "❌ Đóng trình duyệt",
            "reload_page": "🔄 Tải lại",
            "back_page": "⬅️ Quay lại",
            "forward_page": "➡️ Tiến tới"
        }
    },
    "en": {  # Tiếng Anh
        "command_groups": {
            "intro": {
                "title": "⚡️ INTRODUCTION",
                "commands": {
                    "/introduce": "About me."
                }
            },
            "system": {
                "title": "⚡️ SYSTEM CONTROL",
                "commands": {
                    "/shutdown": "Shutdown command.",
                    "/sleep": "Sleep mode command.",
                    "/restart": "Restart command.",
                    "/cancel": "Cancel all commands."
                }
            },
            "image": {
                "title": "⚡️ IMAGE COMMANDS",
                "commands": {
                    "/screen_shot": "Take a screenshot and send it back.",
                    "/record_video": "Record screen video and send it back."
                }
            },
            "file": {
                "title": "⚡️ FILE MANAGEMENT",
                "commands": {
                    "/upload_file": "User sends file to upload to the machine.",
                    "/download_file": "User enters path to download.",
                    "/deletefile": "User enters path to delete file."
                }
            },
            "info": {
                "title": "⚡️ SYSTEM INFORMATION",
                "commands": {
                    "/tasklist": "List of running processes.",
                    "/systeminfo": "System information.",
                    "/netuser": "List of users on the computer.",
                    "/whoami": "Current logged in account name.",
                    "/hostname": "Display computer name."
                }
            },
            "network": {
                "title": "⚡️ NETWORK",
                "commands": {
                    "/ipconfig": "Network configuration information.",
                    "/release": "Release current IP address.",
                    "/renew": "Renew IP address."
                }
            },
            "browser": {
                "title": "⚡️ BROWSER",
                "commands": {
                    "/playvideo": "Play YouTube video from link.",
                    "/openweb": "Open websites.",
                    "/setbrowser": "Select default browser (chrome, brave, edge, opera)."
                }
            },
            "utility": {
                "title": "⚡️ UTILITIES",
                "commands": {
                    "/mouse_virtual_system": "Control mouse with virtual touchpad.",
                    "/volume_virtual_system": "Control volume with virtual touchpad.",
                    "/keyboard_emulator": "Control virtual keyboard.",
                    "/stop_touchpad": "Stop running touchpad.",
                    "/set_language": "Change display language."
                }
            },
            "help": {
                "title": "⚡️ HELP",
                "commands": {
                    "/menu": "Display command list."
                }
            }
        },
        "messages": {
            "permission_denied": "⚠️ You don't have permission to use this bot!\n\nThis bot is only for authorized users.",
            "no_permission_log": "User not allowed to access: ID {user_id}, Name: {user_name}",
            "menu_title": "📋 COMMAND LIST",
            "author": "📌 Author: LePhiAnhDev",
            "set_language_title": "🌐 Select the display language for the bot:",
            "current_language": "Current language: English",
            "already_using_language": "✅ You are already using English, nothing changed.",
            "language_changed": "✅ Switched to English.",
            "introduce_content": "<b>👨‍💻 DEVELOPER | LE PHI ANH</b>\n\n<strong>For any project or work you want to collaborate on, I'm always ready. Contact me now to create great values together!</strong>\n\n<b>📩 CONTACT FOR WORK:</b>\n• Discord: <code>LePhiAnhDev</code>\n• Telegram: <a href='https://t.me/lephianh386ht'>@lephianh386ht</a>\n• GitHub: <a href='https://github.com/LePhiAnhDev'>LePhiAnhDev</a>\n• My Website: <a href='https://lephianh.id.vn/'>lephianh.id.vn</a>\n\n<b>🌟 DONATE ME:</b>\n• 💳 <b>Bank:</b> <code>1039506134</code> | LE PHI ANH | Vietcombank\n• 🏦 <b>MoMo:</b> <code>0971390849</code> | LE PHI ANH\n• 💰 <b>Metamask:</b> <code>0x928F8c5443b13f71a4d7094E8bD2E74c86127243</code>\n\nPress <b>/menu</b> to see command list"
        },
        "touchpad": {
            "missing_libs": "<b>❌ This feature requires Flask and pyngrok.</b>\n<b>Please install libraries with command:</b>\n<code>pip install flask pyngrok</code>",
            "mouse_init_error": "<b>❌ Unable to initialize mouse controller.</b>\n<b>Please check access permissions or run with admin rights.</b>",
            "already_running": "<b>✅ Mouse touchpad is already running!</b>\n\n<b>🔗 Access the following URL on your phone:</b>\n<code>{url}</code>\n\n<b>📱 To control the mouse:</b>\n• Touch and drag on the touchpad screen to move the mouse\n• Press buttons to perform mouse actions\n• Scroll mode allows you to scroll up/down\n\n<b>⚠️ This connection will expire after about 2 hours</b>",
            "stopping_current": "<b>🔄 Stopping {type} touchpad currently running...</b>",
            "cannot_stop": "<b>❌ Cannot stop current touchpad:</b> {message}",
            "stopped_starting_new": "<b>✅ Stopped {message}</b>\n<b>🔄 Starting new mouse touchpad...</b>",
            "starting": "<b>🔄 Starting virtual touchpad via Ngrok, please wait...</b>",
            "flask_started": "<b>✅ Flask web server started successfully.</b>\n<b>🔄 Connecting to Ngrok...</b>",
            "ngrok_error": "<b>❌ Unable to start Ngrok.</b>\n\n<b>Please check your network connection and Ngrok settings.</b>",
            "ready": "<b>✅ Virtual touchpad is ready!</b>\n\n<b>🔗 Access the following URL on your phone:</b>\n{url}\n\n<b>📱 To control the mouse:</b>\n• Touch and drag on the touchpad screen to move the mouse\n• Press buttons to perform mouse actions\n• Scroll mode allows you to scroll up/down\n\n<b>⚠️ This connection will expire after about 2 hours</b>\n<b>💡 Use /stop_touchpad to stop when no longer needed</b>",
            "error_init": "<b>❌ An error occurred when initializing virtual touchpad:</b> {error}",
            "error_ngrok": "<b>❌ Error when starting Ngrok:</b> {error}\n\n<b>Please check Ngrok settings and try again.</b>",
            "none_running": "<b>❌ No touchpad is currently active.</b>\n<b>Start a touchpad first using /mouse_virtual_system or /volume_virtual_system</b>",
            "refreshing": "<b>🔄 Refreshing Ngrok connection, please wait...</b>",
            "refresh_error": "<b>❌ Cannot restart Ngrok.</b>\n\n<b>Please check your network connection and Ngrok settings.</b>",
            "invalid_type": "<b>❌ Invalid touchpad type.</b>",
            "refresh_success": "<b>✅ Connection refreshed successfully!</b>\n\n<b>🔗 Access the new URL on your phone:</b>\n<code>{url}{endpoint}</code>\n\n<b>📱 Usage instructions:</b>\n{action_info}\n\n<b>⚠️ This connection will expire after about 2 hours</b>\n<b>💡 Use /stop_touchpad to stop when no longer needed</b>",
            "refresh_error_general": "<b>❌ Error refreshing connection:</b> {error}",
            "volume_already_running": "<b>✅ Volume touchpad is already running!</b>\n\n<b>🔗 Access the following URL on your phone:</b>\n<code>{url}/volume</code>\n\n<b>📱 Usage instructions:</b>\n• Drag the slider left/right to adjust volume\n• Press buttons to quickly set specific volume levels\n\n<b>⚠️ This connection will expire after about 2 hours</b>",
            "pycaw_error": "<b>❌ Cannot control volume because pycaw library is not available or you are using a non-Windows operating system.</b> <b>Please check library installation and your operating system.</b>",
            "stopped_volume_new": "<b>✅ Stopped {message}</b>\n<b>🔄 Starting new volume touchpad...</b>",
            "starting_volume": "<b>🔄 Starting volume touchpad via Ngrok, please wait...</b>",
            "volume_ready": "<b>✅ Volume control touchpad is ready!</b>\n\n<b>🔗 Access the following URL on your phone:</b>\n{url}/volume\n\n<b>📱 Usage instructions:</b>\n• Drag the slider left/right to adjust volume\n• Press buttons to quickly set specific volume levels\n\n<b>⚠️ This connection will expire after about 2 hours</b>\n<b>💡 Use /stop_touchpad to stop when no longer needed</b>",
            "volume_error_init": "<b>❌ An error occurred when initializing volume touchpad:</b> {error}",
            "no_volume_touchpad": "<b>❌ No volume touchpad is currently active.</b>\n<b>Start a touchpad first using /volume_virtual_system</b>",
            "none_running_stop": "<b>❌ No touchpad is running.</b>",
            "stopping": "<b>🔄 Stopping {type} touchpad...</b>",
            "stop_success": "<b>✅ Successfully stopped {message}.</b>",
            "stop_error": "<b>❌ Cannot stop touchpad: {message}</b>",
            "mouse_instruction": "• Touch and drag on the touchpad screen to move the mouse\n• Press buttons to perform mouse actions\n• Scroll mode allows you to scroll up/down",
            "volume_instruction": "• Drag the slider left/right to adjust volume\n• Press buttons to quickly set specific volume levels"
        },
        "keyboard": {
            "instruction": "<b>⌨️ This is a QWERTY keyboard emulator. Press /menu to return.</b>",
            "key_pressed": "<b>✅ Key pressed:</b> <code>{key}</code>",
            "key_error": "<b>❌ Error when pressing key:</b> {error}"
        },
        "browser": {
            "setbrowser_help": "<b>⚠️ Please enter the website URL you want to open. For example:</b>\n<code>/openweb https://www.google.com</code>\n<b>or</b>\n<code>/openweb google.com</code>",
            "no_browsers": "<b>❌ No browsers found installed on the system.</b>",
            "current_browser": "<b>Current browser:</b> {browser}\n<b>Please select default browser:</b>\n\n<i>Note: Microsoft Edge may have issues and will automatically switch to another browser if errors occur. If you want to use Edge, run the bot with Admin rights and close all open Edge windows first.</i>",
            "set_success": "<b>✅ Set {browser} as default browser.</b>",
            "edge_note": "\n\n<i>Note: Microsoft Edge may have issues. If errors occur, the bot will automatically switch to another browser. To increase success rate, run the bot with Admin rights and close open Edge windows.</i>",
            "browser_not_found": "<b>❌ Browser {browser} not found at: {path}</b>",
            "invalid_browser": "<b>❌ Invalid browser. Please choose Chrome, Brave, Edge or Opera.</b>",
            "youtube_link_help": "<b>⚠️ Please send a YouTube link with the command /playvideo [link].</b>",
            "invalid_youtube": "<b>❌ Invalid YouTube link. Please check and try again.</b>",
            "starting_browser": "<b>🔄 Starting {browser} browser...</b>",
            "browser_started": "<b>✅ Successfully started {browser} browser.</b>",
            "browser_error": "<b>❌ Cannot start browser:</b> {error}",
            "opening_video": "<b>🔄 Opening video with {browser}...</b>",
            "video_opened": "<b>✅ Successfully opened YouTube video on {browser}.</b>",
            "video_not_found": "<b>⚠️ Could not find video player. The page was opened but might not be a YouTube video.</b>",
            "select_action": "<b>🎮 Select action:</b>",
            "url_error": "<b>❌ Cannot open URL.</b> Check network connection or URL.",
            "general_error": "<b>❌ An error occurred:</b> {error}",
            "no_browser_open": "<b>❌ No browser is currently open.</b>",
            "play_pause": "<b>✅ Toggled play/pause state.</b>",
            "rewind": "<b>⏪ Rewound 10 seconds.</b>",
            "forward": "<b>⏩ Forwarded 10 seconds.</b>",
            "browser_closed": "<b>✅ Closed {browser} browser.</b>",
            "video_control_error": "<b>❌ An error occurred while controlling video:</b> {error}",
            "opening_website": "<b>🔄 Opening website {url}...</b>",
            "website_opened": "<b>✅ Opened website {url} in {browser} browser.</b>",
            "page_reloaded": "<b>🔄 Page reloaded.</b>",
            "back_success": "<b>⬅️ Went back to previous page.</b>",
            "back_error": "<b>⚠️ No previous page to go back to.</b>",
            "forward_success": "<b>➡️ Moved forward to next page.</b>",
            "forward_error": "<b>⚠️ No next page to move forward to.</b>",
            "web_control_error": "<b>❌ An error occurred while controlling browser:</b> {error}"
        },
        "system": {
            "confirm_shutdown": "<b>⚠️ Are you sure you want to shut down the computer?</b>",
            "confirm_restart": "<b>⚠️ Are you sure you want to restart the computer?</b>",
            "confirm_sleep": "<b>⚠️ Are you sure you want to put the computer to sleep?</b>",
            "confirm_cancel": "<b>⚠️ Are you sure you want to cancel all shutdown/restart commands?</b>",
            "shutdown_progress": "<b>🔄 Computer will shut down in 3 seconds.</b>",
            "restart_progress": "<b>🔄 Computer will restart in 3 seconds.</b>",
            "cancel_progress": "<b>🔄 Cancelling shutdown/restart commands...</b>",
            "cancel_success": "<b>✅ Successfully cancelled all shutdown/restart commands.</b>",
            "cancel_none": "<b>ℹ️ No commands to cancel.</b>",
            "sleep_progress": "<b>🔄 Computer will go to sleep now.</b>",
            "no_action": "<b>ℹ️ No action performed.</b>",
            "command_error": "<b>❌ An error occurred while executing command:</b> {error}",
            "action_cancelled": "<b>❎ Action cancelled.</b>"
        },
        "screenshot": {
            "taking": "<b>🔄 Taking screenshot...</b>",
            "error": "<b>❌ Cannot take screenshot.</b>",
            "sending": "<b>🔄 Screenshot taken, sending...</b>",
            "saving_error": "<b>❌ Cannot save screenshot.</b>",
            "size_error": "<b>⚠️ Image too large ({size} MB) exceeds Telegram limit (50MB).</b>",
            "sending_progress": "<b>✅ Screenshot is being sent as a file, it will appear in chat after processing completes.</b>",
            "screenshot_error": "<b>❌ An error occurred while taking screenshot:</b> {error}",
            "already_recording": "<b>⚠️ Already recording. Please stop current recording first.</b>",
            "prepare_recording": "<b>🔄 Preparing to record screen (maximum 30 seconds)...</b>",
            "start_error": "<b>❌ Cannot start screen recording.</b>",
            "recording_started": "<b>🎥 Started screen recording (maximum 30 seconds). Press the button below to stop and save video.</b>",
            "no_recording": "<b>❌ No recording process is currently running.</b>",
            "stopping_video": "<b>⏳ Stopping and processing video, please wait...</b>",
            "video_not_found": "<b>❌ Screen recording video file not found.</b>",
            "size_too_large": "<b>❌ Video too large ({size} MB) to send via Telegram (50MB limit).</b> <b>Saved at:</b> <code>{path}</code>",
            "size_too_small": "<b>⚠️ Video appears invalid (size too small: {size} MB).</b> <b>Please try again with a longer recording time.</b>",
            "sending_video": "<b>📤 Sending video...</b>\n<b>(This message will be updated when complete)</b>",
            "video_sent": "<b>✅ Video is being sent in the background, it will appear in chat after processing completes.</b>\n<b>Size:</b> {size} MB",
            "video_error": "<b>❌ Error sending video:</b> {error}\n<b>Saved at:</b> <code>{path}</code>",
            "process_error": "<b>❌ Error processing video:</b> {error}"
        },
        "file": {
            "download_help": "<b>⚠️ Please enter the file path you want to download. Example:</b>\n<code>/download_file D:/example.txt</code>",
            "path_valid": "<b>✅ Valid path. Preparing to send file:</b> <code>{path}</code>",
            "file_too_large": "<b>❌ File too large ({size} MB). Telegram only allows sending files up to 50MB.</b>",
            "sending_file": "<b>🔄 Sending file ({size} MB)...</b>",
            "send_success": "<b>✅ File sent successfully:</b> <code>{path}</code>",
            "send_no_confirm": "<b>⚠️ No confirmation received for file sending.</b>",
            "send_error": "<b>❌ An error occurred while sending file:</b> {error}",
            "file_not_found": "<b>❌ File not found at path:</b> <code>{path}</code>",
            "upload_instruction": "<b>📤 Please send the file you want to upload. File will be saved in</b> <code>{folder}</code>",
            "receiving_file": "<b>🔄 Receiving file...</b>",
            "downloading": "<b>🔄 Downloading file to computer...</b>",
            "upload_success": "<b>✅ File {filename} ({size}) has been downloaded and saved in</b> <code>{folder}</code>",
            "upload_failed": "<b>❌ Cannot download file {filename}.</b>",
            "upload_error": "<b>❌ An error occurred while uploading file:</b> {error}",
            "no_valid_file": "<b>❌ No valid file received. Please try again!</b>",
            "delete_help": "<b>⚠️ Please enter the file path you want to delete. Example:</b>\n<code>/deletefile D:/example.txt</code>",
            "path_not_found": "<b>❌ File or directory not found at path:</b> <code>{path}</code>",
            "delete_success": "<b>✅ File at path</b> <code>{path}</code> <b>has been deleted successfully.</b>",
            "permission_error": "<b>❌ No permission to delete file:</b> <code>{path}</code>. <b>File may be in use by another program.</b>",
            "delete_error": "<b>❌ An error occurred while deleting file:</b> {error}",
            "is_directory": "<b>⚠️ {path} is a directory. This command only deletes files, not directories.</b>",
            "invalid_path": "<b>❓ Path</b> <code>{path}</code> <b>is not a valid file or directory.</b>"
        },
        "system_info": {
            "running_command": "<b>🔄 Running command</b> <code>'{command}'</code><b>...</b>",
            "no_result": "<b>⚠️ Command returned no result or an error occurred.</b>",
            "command_success": "<b>✅ Command executed successfully. File size:</b> {size} KB.",
            "command_error": "<b>❌ An error occurred while running command:</b> {error}",
            "windows_only": "<b>❌ This command is only supported on Windows.</b>"
        },
        "buttons": {
            "confirm": "✅ Confirm",
            "cancel": "❎ Cancel",
            "stop_recording": "⏹️ Stop Recording",
            "refresh_connection": "🔄 Refresh Connection",
            "play_pause": "⏯ Play / Pause",
            "rewind": "⏪ Rewind 10s",
            "forward": "⏩ Forward 10s",
            "close_browser": "❌ Close Browser",
            "reload_page": "🔄 Reload",
            "back_page": "⬅️ Back",
            "forward_page": "➡️ Forward"
        }
    }
}

# Hàm lấy văn bản dịch
def get_text(key, user_id=None, **kwargs):
    """
    Lấy văn bản dịch theo ngôn ngữ người dùng.
    
    Args:
        key (str): Khóa đến văn bản, ví dụ: "messages.permission_denied"
        user_id (int, optional): ID người dùng để xác định ngôn ngữ
        **kwargs: Các tham số để format chuỗi
    
    Returns:
        str: Văn bản đã dịch
    """
    # Xác định ngôn ngữ của người dùng
    from language_config import DEFAULT_LANGUAGE
    language = DEFAULT_LANGUAGE
    if user_id is not None:
        language = get_user_language(user_id)
    
    # Phân tích khóa, ví dụ: "messages.permission_denied"
    parts = key.split('.')
    current = TRANSLATIONS.get(language, TRANSLATIONS[DEFAULT_LANGUAGE])
    
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            # Trả về khóa gốc nếu không tìm thấy
            logger.warning(f"Không tìm thấy khóa dịch: {key} cho ngôn ngữ {language}")
            # Thử với ngôn ngữ mặc định
            if language != DEFAULT_LANGUAGE:
                current = TRANSLATIONS[DEFAULT_LANGUAGE]
                for part in parts:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        return key
            else:
                return key
    
    # Nếu chuỗi có các placeholder, thay thế bằng các giá trị từ kwargs
    if isinstance(current, str) and kwargs:
        try:
            current = current.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Thiếu tham số format cho chuỗi '{key}': {e}")
    
    return current

# Hàm lấy nhóm lệnh theo ngôn ngữ người dùng
def get_command_groups(user_id):
    language = get_user_language(user_id)
    return TRANSLATIONS[language]["command_groups"]

# Tạo từ điển lệnh từ các nhóm lệnh
def get_commands(user_id):
    commands = {}
    command_groups = get_command_groups(user_id)
    for group in command_groups.values():
        commands.update(group["commands"])
    return commands
