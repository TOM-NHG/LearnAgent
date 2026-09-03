# Báo cáo phân tích và chất lượng dữ liệu

Ngày phân tích: 30/08/2026  
Phạm vi: toàn bộ thư mục `data`

## 1. Tổng quan

Bộ dữ liệu mô phỏng hoạt động tài chính – học phí của một trường đại học. Dữ liệu gồm 5 bảng nghiệp vụ/danh mục, một manifest ghi nhận lỗi, một file tổng hợp quá trình sinh dữ liệu và mã nguồn tạo dữ liệu.

| File | Số dòng | Vai trò |
|---|---:|---|
| `dim_students.csv` | 1.500 | Danh mục sinh viên |
| `dim_departments.csv` | 20 | Danh mục khoa/phòng ban |
| `fact_tuition_invoices.csv` | 3.000 | Hóa đơn học phí |
| `fact_payments.csv` | 3.500 | Giao dịch thanh toán |
| `fact_expenses.csv` | 2.000 | Chi phí khoa/phòng ban |
| `data_quality_manifest.csv` | 1.086 | Nhật ký lỗi được cài vào dữ liệu |

Tổng dữ liệu nghiệp vụ: **10.020 dòng**. Vì nguồn là CSV nên kiểu vật lý không được khai báo; các kiểu bên dưới là kiểu logic đề xuất khi nhập database hoặc data warehouse.

## 2. Data dictionary

### 2.1. `dim_students`

| Field | Kiểu đề xuất | Ý nghĩa / miền giá trị |
|---|---|---|
| `Student_ID` | `VARCHAR`, PK | Mã sinh viên, dạng `STU000001` |
| `Full_Name` | `NVARCHAR` | Họ tên; có lỗi hoa/thường và khoảng trắng |
| `Date_Of_Birth` | `DATE` | Ngày sinh, 1998–2007 |
| `Gender` | Enum | `Male`, `Female`, `Other` |
| `Email` | `VARCHAR` | Email cá nhân |
| `Phone` | `VARCHAR` | Số điện thoại, đang có nhiều kiểu định dạng |
| `Department_ID` | `VARCHAR`, FK | Khoa đào tạo, tham chiếu `dim_departments` |
| `Major` | `NVARCHAR` | Chuyên ngành; 12 giá trị, có null |
| `Enrollment_Date` | `DATE` | Ngày nhập học, 2019–2025 |
| `Status` | Enum | `Active`, `Graduated`, `Suspended`, `Dropped Out` |
| `Dropout_Date` | `DATE NULL` | Ngày nghỉ học, chỉ áp dụng cho `Dropped Out` |

Phân bố trạng thái: 902 Active, 266 Graduated, 205 Dropped Out và 127 Suspended.

### 2.2. `dim_departments`

| Field | Kiểu đề xuất | Ý nghĩa |
|---|---|---|
| `Department_ID` | `VARCHAR`, PK | Mã khoa/phòng, `DEP001`–`DEP020` |
| `Department_Name` | `NVARCHAR` | Tên khoa/phòng |
| `Faculty_Name` | `NVARCHAR` | Khối quản lý |
| `Manager_Name` | `NVARCHAR` | Người quản lý |
| `Annual_Budget` | `DECIMAL(18,0)` | Ngân sách năm, khoảng 2,379–19,103 tỷ đồng |
| `Created_Date` | `DATE` | Ngày thành lập, 2001–2018 |

### 2.3. `fact_tuition_invoices`

| Field | Kiểu đề xuất | Ý nghĩa |
|---|---|---|
| `Invoice_ID` | `VARCHAR`, PK | Mã hóa đơn |
| `Student_ID` | `VARCHAR`, FK | Sinh viên nhận hóa đơn |
| `Semester` | Enum | `HK1`, `HK2`, `HK Hè` |
| `Academic_Year` | `CHAR(9)` | Năm học, ví dụ `2025-2026` |
| `Invoice_Date` | `DATE` | Ngày lập hóa đơn |
| `Due_Date` | `DATE` | Hạn thanh toán |
| `Tuition_Fee` | `DECIMAL(18,0)` | Học phí gốc, 8,007–34,990 triệu |
| `Scholarship_Amount` | `DECIMAL(18,0)` | Số tiền học bổng được trừ |
| `Late_Fee` | `DECIMAL(18,0)` | Phí trễ hạn |
| `Total_Amount` | `DECIMAL(18,0)` | Học phí − học bổng + phí trễ |
| `Invoice_Status` | Enum | `Issued`, `Partially Paid`, `Paid`, `Overdue` |

### 2.4. `fact_payments`

| Field | Kiểu đề xuất | Ý nghĩa |
|---|---|---|
| `Payment_ID` | `VARCHAR`, PK | Mã giao dịch |
| `Invoice_ID` | `VARCHAR`, FK | Hóa đơn được thanh toán |
| `Student_ID` | `VARCHAR`, FK | Sinh viên thanh toán |
| `Payment_Date` | `DATE NULL` | Ngày thanh toán |
| `Payment_Method` | Enum | `Bank Transfer`, `Cash`, `Card`, `E-Wallet` |
| `Amount_Paid` | `DECIMAL(18,0)` | Số tiền giao dịch, 1,158–86,788 triệu |
| `Transaction_Reference` | `VARCHAR` | Mã tham chiếu giao dịch |
| `Payment_Status` | Enum | `Successful`, `Pending`, `Failed`, `Reversed` |

Phân bố trạng thái: 3.010 Successful, 211 Failed, 187 Pending và 92 Reversed.

### 2.5. `fact_expenses`

| Field | Kiểu đề xuất | Ý nghĩa |
|---|---|---|
| `Expense_ID` | `VARCHAR`, PK | Mã khoản chi |
| `Department_ID` | `VARCHAR`, FK | Khoa/phòng chịu chi phí |
| `Expense_Date` | `DATE` | Ngày phát sinh |
| `Expense_Category` | Enum | Salary, Equipment, Maintenance, Utilities, Research, Marketing, Scholarship, Office Supplies |
| `Vendor_Name` | `NVARCHAR` | Nhà cung cấp |
| `Description` | `NVARCHAR` | Nội dung chi |
| `Amount` | `DECIMAL(18,0)` | Số tiền; tối đa bất thường 96,9865 tỷ |
| `Approval_Status` | Enum | `Approved`, `Pending`, `Rejected` |
| `Payment_Method` | Enum | `Bank Transfer`, `Cash`, `Corporate Card` |

### 2.6. `data_quality_manifest`

| Field | Ý nghĩa |
|---|---|
| `Table_Name` | Bảng chứa lỗi |
| `Record_ID` | Mã bản ghi bị ảnh hưởng |
| `Error_Type` | Loại lỗi |
| `Column_Name` | Cột bị ảnh hưởng |
| `Original_Value` | Giá trị trước khi làm bẩn |
| `Corrupted_Value` | Giá trị sau khi làm bẩn |
| `Description` | Diễn giải lỗi |

## 3. Lỗi được ghi trong manifest

| Loại lỗi | Số sự kiện |
|---|---:|
| Ngày có nhiều định dạng | 557 |
| Chuỗi không đồng nhất | 122 |
| Thiếu ngày thanh toán | 88 |
| Thanh toán trước ngày hóa đơn | 70 |
| Một giao dịch vượt giá trị hóa đơn | 70 |
| Thanh toán sau khi sinh viên nghỉ học | 60 |
| Thiếu chuyên ngành | 45 |
| Dòng trùng hoàn toàn | 40 |
| Sai công thức tổng hóa đơn | 30 |
| Chi phí bị nhân 100 | 4 |

## 4. Lỗ hổng chất lượng thực tế

### 4.1. Trùng lặp và khóa chính

- Có 40 dòng trùng hoàn toàn: 10 sinh viên, 15 hóa đơn và 15 khoản chi.
- Các dòng này làm vi phạm tính duy nhất của khóa chính và có thể làm tăng sai tổng doanh thu, công nợ và chi phí.
- `Payment_ID`, `Transaction_Reference` và `Department_ID` hiện vẫn duy nhất.

### 4.2. Thiếu dữ liệu

- Có 47 dòng sinh viên thiếu `Major`, cao hơn 45 sự kiện trong manifest vì một số dòng lỗi được sao chép khi tạo duplicate.
- Có 88 giao dịch thiếu `Payment_Date`.

### 4.3. Sai số tiền và đối soát công nợ

- 30 hóa đơn không thỏa `Total_Amount = Tuition_Fee - Scholarship_Amount + Late_Fee`.
- 70 giao dịch đơn lẻ có `Amount_Paid > Total_Amount` của hóa đơn.
- 706 hóa đơn có tổng các giao dịch `Successful` vượt `Total_Amount`.
- Kiểm tra một giao dịch đơn lẻ là chưa đủ; cần kiểm soát số tiền cộng dồn theo hóa đơn và xử lý giao dịch `Reversed`.

### 4.4. Lỗi thời gian

- Có 557 giá trị ngày dùng lẫn `YYYY-MM-DD` và `DD/MM/YYYY`.
- Sau khi đọc đúng từng định dạng, có 104 thanh toán trước ngày hóa đơn.
- Có 340 thanh toán sau ngày sinh viên nghỉ học.
- Không có hóa đơn trước ngày nhập học.
- Không có `Due_Date` trước `Invoice_Date` khi ngày được parse đúng.
- So với ngày phân tích 30/08/2026, có 784 hóa đơn tương lai, 952 thanh toán tương lai và 17 ngày nghỉ học tương lai. Năm học kéo tới `2030-2031`.

### 4.5. Chuỗi không chuẩn hóa

- Có 122 sự kiện viết hoa toàn bộ, viết thường hoặc khoảng trắng thừa trong họ tên, tên quản lý và nhà cung cấp.
- Số điện thoại sử dụng nhiều cách trình bày khác nhau.
- Nếu không trim và chuẩn hóa Unicode/case trước khi nhóm dữ liệu, cùng một thực thể có thể bị tính thành nhiều nhóm.

### 4.6. Ngoại lệ chi phí

- Có 4 khoản chi bị nhân 100.
- Giá trị cao nhất gần 97 tỷ đồng.
- Trung bình `Amount` khoảng 268,8 triệu, trong khi trung vị khoảng 105,2 triệu; các ngoại lệ làm méo mạnh số trung bình.

## 5. Lỗ hổng thiết kế và nghiệp vụ

- `Invoice_Status` được sinh độc lập, chưa được tính lại từ số tiền thanh toán, hạn thanh toán và trạng thái giao dịch.
- Chưa có cơ chế khóa hoặc kiểm soát tổng thanh toán vượt công nợ.
- `Student_ID` được lặp lại trong payment dù có thể suy ra từ invoice; nếu thiếu constraint, hai giá trị có thể không khớp trong tương lai.
- Không có trường `Currency`; đơn vị VND chỉ là suy đoán từ miền giá trị.
- Không có `Created_At`, `Updated_At`, nguồn dữ liệu, người chỉnh sửa hoặc version để audit.
- `Annual_Budget` không có năm ngân sách.
- Expense thiếu số chứng từ, hóa đơn nhà cung cấp, người phê duyệt và ngày phê duyệt.
- Hóa đơn không có bảng dòng chi tiết học phí.
- Chưa có quy tắc định dạng/validation rõ ràng cho email, điện thoại và tên.
- `Description` của chi phí là câu sinh tự động, ít giá trị nghiệp vụ.
- `Gender = Other` chiếm 537/1.500 dòng, khoảng 35,8%; phân phối này có vẻ ngẫu nhiên và không phù hợp nếu dùng để suy luận thống kê thực tế.

## 6. Bảo mật và dữ liệu cá nhân

- Bảng sinh viên chứa họ tên, ngày sinh, email và số điện thoại của toàn bộ 1.500 dòng.
- Bảng thanh toán chứa 3.500 mã tham chiếu giao dịch.
- Chưa thấy dấu hiệu masking, mã hóa, phân quyền theo vai trò, chính sách lưu giữ hay nhật ký truy cập.
- Cần phân loại dữ liệu cá nhân, giới hạn quyền truy cập và masking trước khi chuyển sang môi trường phân tích/test.

## 7. Tính toàn vẹn đang đạt

- Tất cả `Department_ID` của sinh viên và chi phí đều tồn tại trong bảng phòng ban.
- Tất cả `Student_ID` của hóa đơn đều tồn tại trong bảng sinh viên.
- Tất cả `Invoice_ID` và `Student_ID` trong payment đều tìm thấy bản ghi cha.
- `Student_ID` trong payment hiện khớp với sinh viên của invoice.
- Sinh viên `Dropped Out` đều có `Dropout_Date`; các trạng thái khác không có ngày nghỉ học.

## 8. Vấn đề file và quy trình sinh dữ liệu

- `finance_dirty_dataset_bundle.zip` có kích thước 0 byte: file bundle bị rỗng hoặc quá trình đóng gói chưa hoàn thành.
- Mã nguồn tạo dữ liệu khai báo xuất vào `data/output`, nhưng CSV hiện nằm trực tiếp trong `data`; cấu trúc đầu ra không đồng nhất hoặc đã có bước di chuyển thủ công.
- Manifest chỉ ghi nhận sự kiện được chủ động cài vào dữ liệu, không đại diện đầy đủ cho tất cả vi phạm cuối cùng sau khi duplicate và các phép biến đổi chồng lấn.

## 9. Khuyến nghị ưu tiên

1. Chuẩn hóa toàn bộ ngày về ISO `YYYY-MM-DD` trước khi kiểm tra logic.
2. Loại duplicate theo khóa nghiệp vụ và tạo constraint `PRIMARY KEY`/`UNIQUE`.
3. Tính lại `Total_Amount`; cách ly 30 hóa đơn sai công thức.
4. Đối soát tổng thanh toán Successful/Reversed theo từng hóa đơn và chặn overpayment.
5. Tính lại `Invoice_Status` từ công nợ thực tế thay vì tin trực tiếp giá trị nguồn.
6. Xác minh hoặc loại các ngày tương lai nếu dữ liệu không phải forecast.
7. Trim, chuẩn hóa Unicode/case, email và điện thoại.
8. Bổ sung constraint ngày, số tiền không âm, miền enum và khóa ngoại ở database.
9. Mask dữ liệu cá nhân trong môi trường thử nghiệm và áp dụng phân quyền truy cập.
10. Đưa các kiểm tra chất lượng vào pipeline và tạo báo cáo lỗi sau cùng thay vì chỉ dùng manifest lúc sinh dữ liệu.
