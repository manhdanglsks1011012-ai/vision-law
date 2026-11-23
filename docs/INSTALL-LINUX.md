# Cài Vision law 1.0 cho Linux

Bản này được build và kiểm tra trên Ubuntu 26.04 x86-64 (glibc 2.43). Không cần cài Python/PyQt6. Chưa xác nhận chạy trên Ubuntu 24.04, hệ khác hoặc Windows.

Trước khi dùng: đóng phiên Vision law cũ. Giữ bản sao vault ở nơi khác.

## Cách khuyến nghị: cài cho tài khoản hiện tại

1. Giải nén `vision-law-1.0.0-linux-x86_64.tar.gz`.
2. Mở Terminal trong thư mục vừa giải nén và chạy `./install-user.sh`.
3. Mở **Vision law** từ menu ứng dụng. Launcher phát triển cũ được thay thế và có bản sao dự phòng.

Có thể chạy trực tiếp `./app/vision-law` không cần cài. Không di chuyển riêng tệp chạy ra khỏi thư mục `app`, vì `_internal` chứa thư viện cần thiết. Bản đầu không có vault sẽ tạo vault chào mừng trong vùng dữ liệu cá nhân; sau đó mở vault của bạn từ tên vault ở góc trái.

Gỡ bản cài cá nhân: chạy `./uninstall-user.sh` trong thư mục giải nén. Lệnh chỉ gỡ binary/launcher do trình cài tạo, không xóa vault hoặc cấu hình. Có thể giữ các phiên bản trước trong thư mục releases để quay lại; luôn sao lưu vault trước khi đổi bản ứng dụng.

## Gói Debian/Ubuntu

Có thể mở `vision-law_1.0.0_amd64.deb` bằng trình cài gói, hoặc dùng `sudo apt install ./vision-law_1.0.0_amd64.deb`. Gỡ bằng `sudo apt remove vision-law`. Ghi chú cá nhân không nằm trong gói và không bị gỡ theo ứng dụng.

Nếu đã dùng launcher phát triển tại `~/.local/share/applications/vision-law.desktop`, launcher cá nhân có thể che launcher hệ thống. Dùng cách cài cá nhân ở trên để cập nhật launcher đó, hoặc lưu bản sao rồi bỏ launcher phát triển trước khi dùng gói .deb.

## Khi gặp lỗi

Log: thư mục dữ liệu ứng dụng `Vision law/logs/` trong `$XDG_DATA_HOME` (mặc định `~/.local/share`). Bản nháp chưa lưu được sao chép định kỳ 5 giây vào `Vision law/recovery/`. Lần mở lại vault sẽ đề nghị khôi phục vào vùng soạn thảo để kiểm tra, không tự ghi đè ghi chú. Bỏ qua vẫn giữ bản sao lưu trữ.

Mỗi vault chỉ cho một phiên Vision law ghi cùng lúc. Nếu app bị dừng đột ngột, khóa quá trình cũ được kiểm tra khi mở lại. Không sửa cùng tệp đồng thời bằng Vision law và Obsidian; ứng dụng vẫn phát hiện thay đổi bên ngoài trước khi lưu.

Một tệp .vlaw cần đi cùng các .md được tham chiếu với cấu trúc đường dẫn giữ nguyên. Mở Markdown bằng Obsidian thấy phần Dẫn chiếu dự phòng; màu/vị trí/cổng của bảng vẫn thuộc .vlaw.
