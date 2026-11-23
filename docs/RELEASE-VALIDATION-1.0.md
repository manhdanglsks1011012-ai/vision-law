# Vision law 1.0.0 — kiểm tra phát hành

Mục tiêu: giữ nguyên tính năng đã duyệt, kiểm tra lưu trữ và tạo bản Linux độc lập. Không có phần mềm được bảo đảm tuyệt đối không lỗi.

## Phạm vi

Máy xây dựng và kiểm tra: Ubuntu 26.04.1 LTS, x86_64, glibc 2.43; Python 3.14.4, PyQt6/Qt 6.10.2; PyInstaller 6.22.3. Bản chạy đã kèm Python và Qt. Chưa xác nhận trên Windows hoặc Linux cũ hơn. PyInstaller không đóng gói glibc: xem [tài liệu chính thức](https://pyinstaller.org/en/stable/usage.html).

## Gia cố

- Lưu qua tệp tạm, fsync và thay thế nguyên tử; giữ quyền truy cập tệp cũ. Khi thay thế thất bại, dữ liệu cũ còn nguyên.
- Kiểm tra cấu trúc bảng, tọa độ hữu hạn và đường dẫn trước khi ghi; chặn thư mục dữ liệu là symlink trỏ ra ngoài vault.
- Khóa vault để hai phiên Vision law không cùng sửa một vault.
- Bản nháp chưa lưu được chụp mỗi 5 giây; khi mở lại, đề nghị khôi phục vào trình soạn thảo để kiểm tra, không tự ghi đè tệp gốc.
- Nhật ký lỗi cục bộ có giới hạn dung lượng. Lỗi trong thao tác Qt được ghi lại, giữ bản nháp và thông báo.
- Tránh vòng lặp tô định dạng/ghi tự động; giữ kiểm thử hồi quy lỗi mở ghi chú có liên kết cũ. Giảm số điểm lưới khi thu nhỏ.
- Điểm khởi chạy riêng tránh tải hai bản định nghĩa lớp khi chạy ứng dụng.

## Kiểm thử

Bộ unittest bao gồm lưu/di chuyển/xóa tệp, bảng độc lập, liên kết và phân loại, xuất Markdown, editor, chuyển trang, nối lại đường ống, chống treo khi mở ghi chú và khôi phục bản nháp. Bài tải tạo 300 ghi chú và 299 liên kết, mở/sửa/lưu/mở lại; giới hạn thời gian khởi tạo 20 giây.

Kết quả thực tế và kiểm tra bản đóng gói được ghi ở `TEST-RESULTS.txt` đi kèm. Kiểm tra binary dùng cấu hình người dùng mới, môi trường tối giản và Qt offscreen trên máy xây dựng; đây chưa phải kiểm thử trong máy ảo hệ điều hành sạch. Chưa tự động xác nhận cảm giác touchpad, hiển thị Wayland thực tế hoặc thao tác kéo thả bằng tay của bản đóng gói.

## Giới hạn còn lại

Khóa chỉ áp dụng giữa các phiên Vision law, không khóa Obsidian hay trình sửa tệp bên ngoài. Lưu nguyên tử áp dụng từng tệp, không phải giao dịch nhiều tệp. Bản nháp có thể thiếu thay đổi trong khoảng 5 giây cuối trước khi máy bị ngắt đột ngột; bố trí các cửa sổ ghi chú đang mở chưa được phục hồi đầy đủ. Hãy giữ bản sao vault định kỳ.

Bản chuẩn bị phát hành công khai. Thông báo bản quyền Python, PyQt, Qt và công cụ build được kèm theo; cần xem lại điều kiện giấy phép trước khi phân phối thương mại/công khai. Mã nguồn Vision law được cung cấp cùng bản portable theo GPL-3.0-only do chủ dự án lựa chọn.
