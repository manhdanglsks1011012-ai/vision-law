# Vision law

Ứng dụng desktop Linux để ghi chú Markdown và tổ chức kiến thức trên bảng bo mạch. Bản 1.0.0 đóng gói cho Ubuntu 26.04 x86_64; chưa kiểm tra trên Windows.

Bản cài và portable nằm trong `release/`. Xem [hướng dẫn cài Linux](docs/INSTALL-LINUX.md) và [báo cáo kiểm tra](docs/RELEASE-VALIDATION-1.0.md). Bản đóng gói không cần cài Python.

## Chạy

```bash
cd /home/alexdang/Codex/vision-law
./run.sh
```

Khi chạy từ mã nguồn: dùng Python 3.14 và PyQt6 6.10.2 như môi trường đã kiểm tra. Mặc định mở `demo-vault`. Bấm tên vault phía dưới sidebar để mở/tạo vault khác; tối đa 8 vault gần đây được nhớ. Có launcher `vision-law.desktop` trong thư mục dự án. Logo là tinh thể bảy màu riêng, ở `assets/vision-law.svg`.

## Tệp và sao lưu

- `.md`: nội dung ghi chú, tiêu đề/mô tả thẻ và dẫn chiếu dự phòng cho Obsidian.
- `.vlaw`: mỗi bảng là một tệp riêng, chứa đường dẫn các ghi chú, bố cục, quan hệ, cổng nối, danh mục, màu/bậc và góc nhìn. Không sao chép nội dung ghi chú.
- `.vision-law/board-files.json`: phiên làm việc và mẫu nhóm dùng chung.
- `.vision-law/backups/`: bản gần nhất trước sửa nội dung; `reference-backups/`: bản trước lần đầu thêm dẫn chiếu; `board-backups/`: bản trước sửa bảng.
- `.trash/`: tệp/thư mục đã chuyển vào thùng rác và danh sách khôi phục.

Tệp được ghi qua tệp tạm và thay thế. Có kiểm tra thay đổi bên ngoài để tránh ghi đè. Chưa có khóa giao dịch giữa nhiều ứng dụng; tránh sửa cùng tệp đồng thời. Bản nháp phục hồi được chụp mỗi 5 giây, có thể thiếu những thay đổi cuối trước khi tắt đột ngột.

Dữ liệu bảng cũ tự chuyển từ `.vision-law/boards.json` sang `.vlaw`; bản gốc giữ ở `boards-before-independent-files.json`. Bảng cũ không tự xuất hiện lại khi xóa tệp bảng sau chuyển đổi. Muốn chuyển máy, giữ cấu trúc thư mục của `.vlaw` và các `.md` được tham chiếu.

## Cây tệp, xóa và khôi phục

Bấm ghi chú để mở; bấm thư mục để mở/thu gọn. Thư mục đứng trước; trạng thái mở rộng được nhớ theo vault. Tên vault căn trái. Nút cạnh tên vault và trên thanh dọc ẩn/hiện sidebar.

Chuột phải để tạo ghi chú/thư mục/bảng, di chuyển, đổi tên (F2), sao chép đường dẫn. Kéo thả để di chuyển. Đổi tên/di chuyển cập nhật các tham chiếu xác định được trong bảng và wikilink; chưa cập nhật đường dẫn Markdown dạng `[text](path)`.

Chọn mục và nhấn **Delete**, hoặc chuột phải → **Chuyển vào thùng rác**. Có xác nhận trước khi chuyển; xóa thư mục bao gồm các mục con. Không xóa vĩnh viễn. Chuột phải → **Khôi phục từ thùng rác…** để chọn mục. Nếu vị trí gốc đã tồn tại, ứng dụng từ chối ghi đè. Tham chiếu/vị trí nút được giữ để dùng lại khi khôi phục.

## Bảng kiến thức

Mỗi tab trên app gốc là một bảng. Dấu `+` tạo bảng trắng; **Mở bảng** hoặc bấm `.vlaw` trong cây tệp để mở lại. Có đổi tên, di chuyển và **Nhân bản bảng**. Đóng tab không xóa tệp bảng. **Thêm từ thư mục** cho chọn nhiều thư mục/ghi chú; một ghi chú có thể xuất hiện trên nhiều bảng với bố cục khác nhau.

- Kéo nút để bố trí; kéo nền hoặc vuốt hai ngón để di chuyển.
- Chụm/xòe hai ngón hoặc Ctrl+cuộn để zoom. Nút `− / +`, ô phần trăm (1–300%) và **Toàn cảnh** cũng hỗ trợ zoom. Nhập 100 để về kích thước gốc. Vuốt dùng hệ số 60%, zoom 45%; pinch cần desktop Linux gửi cử chỉ phù hợp.
- Ctrl+Z/Ctrl+Y hoàn tác/làm lại thay đổi bảng, gồm góc nhìn và zoom. Tối đa 100 trạng thái mỗi bảng trong phiên chạy, gộp thao tác liên tục theo khoảng nghỉ 350ms. Không xóa tệp Markdown khi hoàn tác việc thêm nút.
- Bấm một lần nút để chọn màu/bậc; nhấp đúp để mở ghi chú.

Màu/bậc: T1 đỏ Legendary; T2 hồng Mythic; T3 cam Ancient; T4 vàng kim Exalted; T5 vàng nhạt Exceptional; T6 tím Epic; T7 xanh dương Rare; T8 xanh ngọc Refined; T9 xanh lá Uncommon; T10 xám Normal. Có thể chọn màu riêng; đổi bậc áp lại màu chuẩn.

## Đường ống

Bấm `+` nguồn, di chuột, bấm `+` đích để nối; hoặc giữ/kéo/thả. Cổng lớn lên khi rê chuột. Bấm nền hoặc Esc hủy. Đường ống chỉ dùng ngang/dọc và góc vuông, mũi tên chạy nguồn → đích.

Phía trên đường ống là nhãn danh mục, đồng bộ với lược đồ. Phía dưới có ghi chú riêng tùy chọn, bật/tắt trong hộp chỉnh liên kết; tắt không xóa chữ đã nhập. Bấm ống để chọn danh mục/màu/chú giải; chuột phải để chuyển cổng/xóa. Bấm nhanh 3 lần để bỏ quan hệ (bật/tắt trong cài đặt). Khi bật, bấm đơn chờ khoảng nhận diện bấm liên tiếp của hệ thống.

Kéo đoạn ống gần đầu nối rồi thả lên `+` khác của cùng ghi chú để đổi cổng, giữ tên/màu/chiều. Nếu nhiều đường chung cổng, chuột phải `+` để chọn đường cần chuyển. Bấm nền hoặc Esc hủy và phục hồi đường cũ.

## Soạn thảo và lược đồ

Vùng giữa liền mạch: tiêu đề lớn → mô tả nhỏ → nội dung. Có Markdown trực tiếp cho tiêu đề `#`–`######`, đậm, nghiêng, gạch bỏ, tô sáng, mã, trích dẫn, danh sách và checklist. Enter tiếp tục danh sách; mục rỗng kết thúc. Tab/Shift+Tab tăng/giảm cấp nhiều dòng. Gạch chân lưu bằng `<u>…</u>`.

- Ctrl+B đậm, Ctrl+I nghiêng, Ctrl+1–6 tiêu đề.
- **Ctrl+E** chuyển đọc/viết, giữ nguyên xuống dòng đơn và số dòng trắng trong chế độ đọc.
- Ctrl+S lưu; có trạng thái lưu nhỏ và menu ⋯ cho định dạng/chế độ đọc/mẫu nhóm. Tự lưu sau 2 giây là tùy chọn, mặc định tắt.
- Khi chuyển tài liệu, nội dung không tự nhận con trỏ; bấm trực tiếp vùng viết để soạn.

Lược đồ trái: hiện tại → đích; phải: nguồn → hiện tại. Nhóm mặc định: **Chưa phân loại, Giải thích, Ví dụ minh họa, Phản biện, Ngoại lệ**. Thêm danh mục riêng, đổi tên/màu/thứ tự, lưu mẫu nhóm. Mỗi nhóm chỉ liệt kê tiêu đề; tooltip chứa đường dẫn/chú giải. Có số lượng, thu gọn và Xem thêm. Nhóm rỗng tự thu gọn.

Chuột phải tiêu đề → **Phân loại quan hệ…** để chọn một hoặc nhiều nhóm. Phân loại thuộc cặp có hướng và bảng, được phản ánh ở cả hai ghi chú. Nhấn `+` trong nhóm để nhập `[[`: gợi ý theo tiêu đề/đường dẫn, đổi phạm vi ngay khi gõ (vault/thư mục/nhánh), ↑ ↓ và Enter để chọn; có tạo ghi chú mới. Phần giữa không cho tạo wikilink mới. Phạm vi **Tất cả bảng** tổng hợp quan hệ và xem tên bảng trong tooltip.

## Dự phòng một chiều sang Obsidian

Khi mở vault, các quan hệ hiện có được rà và ghi thành phần **Dẫn chiếu** trong Markdown nguồn, có `[[đường dẫn]]`, danh mục, chú giải và tên bảng. Quan hệ mới cập nhật tự động. Một đích chỉ có một mục dự phòng; nếu thân bài đã có cùng wikilink thì không thêm wikilink trùng.

Vision law ẩn phần này khỏi vùng giữa; Obsidian đọc được bằng Markdown thông thường. Dẫn chiếu dự phòng giữ lại khi bỏ quan hệ khỏi bảng để tránh mất dữ liệu. Không tự đồng bộ ngược bố cục từ Obsidian. Không sửa các dấu `vision-law-references:start/end` hoặc JSON trong HTML comment. Cập nhật phần dự phòng không gây xung đột giả với bản nháp đang soạn; sửa nội dung thật từ bên ngoài vẫn bị phát hiện.

## Cửa sổ ghi chú nội bộ

Các cửa sổ nằm trong app, không tạo cửa sổ riêng của hệ điều hành. Thanh tab mỏng có tay nắm di chuyển, mở thêm, chia đôi và menu quản lý cửa sổ. Kéo góc dưới phải để đổi kích thước. Kéo tab để sắp xếp; kéo ra bàn để tách cửa sổ; kéo sang thanh tab khác để chuyển. Chuột phải tab có các lựa chọn tương tự.

**Chia đôi** chỉ giữ tiêu đề, mô tả và nội dung, cuộn độc lập; Ctrl+S vẫn lưu. Thoát chia đôi khôi phục lược đồ. Chuyển/tách tab giữ bản nháp.

Giữ **Tab**, bấm **Space** để hiện bảng chọn hình thu nhỏ theo cửa sổ vừa dùng. Bấm Space tiếp để đổi lựa chọn; thả Tab để mở; Esc hủy. Bảng chính cũng là một lựa chọn. Phím trong bảng chọn không lọt vào nội dung. Bố trí cửa sổ/nhóm tab ghi chú chưa phục hồi sau khi thoát app.

## Cài đặt và kiểm tra

Bánh răng trên thanh dọc: nơi tạo ghi chú, cỡ chữ, tự lưu, lưới, bỏ liên kết bằng 3 lần bấm, phím tắt. Mặc định Ctrl+N ghi chú mới; Ctrl+Shift+N thư mục; Ctrl+Shift+F tìm; Ctrl+O vault; Ctrl+, cài đặt. Cấu hình máy dùng QSettings.

```bash
QT_QPA_PLATFORM=offscreen python3 -m unittest -q
```

Kiểm tra Qt offscreen bao gồm dữ liệu, xung đột, chuyển đổi bảng, thùng rác/khôi phục, soạn thảo, dòng trắng, quan hệ, camera/lịch sử và cửa sổ/tab. Cử chỉ touchpad, kéo thả thực tế và icon dock cần kiểm tra trên máy Linux thật. Chưa tương đương toàn bộ Live Preview của Obsidian; chưa hỗ trợ đầy đủ bảng/ảnh/công thức/plugin, cộng tác, đồng bộ hay bộ cài độc lập.
