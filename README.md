# Hanoi Spatial LLM — Hệ thống Hỏi đáp Không gian & Định tuyến Hà Nội

> Hệ thống trợ lý thông minh hỗ trợ phân tích dữ liệu không gian địa lý thành phố Hà Nội trên nền tảng **OpenStreetMap (OSM)**, **PostgreSQL / PostGIS**, **pgRouting** và mô hình ngôn ngữ lớn **Qwen 3.5**.

---

## Tính năng nổi bật

- **Text-to-Spatial-SQL:** Tự động chuyển đổi câu hỏi tự nhiên tiếng Việt sang các truy vấn không gian PostGIS phức tạp (khoảng cách, giao cắt, chứa, vùng đệm, thống kê đa bảng...).
- **Multi-turn Context Memory:** Ghi nhớ ngữ cảnh hội thoại đa lượt. Tự động kế thừa địa giới hành chính hoặc các đối tượng đã lọc ở các câu hỏi trước (ví dụ: *"Có bao nhiêu trường ở Yên Hòa?"* $\rightarrow$ *"Các trường học nào?"*).
- **Định tuyến thông minh (pgRouting):** Tích hợp thuật toán Dijkstra tìm đường đi ngắn nhất, tự động nhận diện và cấm đi ngược đường một chiều, hỗ trợ gộp đoạn đường và tính tổng chiều dài thực tế.
- **Bản đồ tương tác trực quan:** Vẽ tự động và làm nổi bật các thực thể hình học (Point, LineString, MultiPolygon) kèm thông tin thuộc tính chi tiết (Popup) và chú giải màu sắc chuyên nghiệp.
- **Tối ưu hóa chỉ mục GiST:** Toàn bộ 7 lớp dữ liệu chuyên đề được cắt lọc chuẩn địa giới Hà Nội và đánh chỉ mục không gian GiST, phản hồi trong vài chục mili-giây.

---

## Kiến trúc & Công nghệ sử dụng

| Thành phần | Công nghệ / Thư viện | Vai trò |
| :--- | :--- | :--- |
| **Backend** | Python 3.14, FastAPI, Uvicorn | Xây dựng RESTful API và điều phối xử lý nghiệp vụ |
| **Database** | PostgreSQL 18 + PostGIS 3.5 + pgRouting | Lưu trữ và xử lý truy vấn dữ liệu không gian, đồ thị mạng lưới |
| **AI Engine** | OpenAI API Client + Model Qwen 3.5 | Dịch ngôn ngữ tự nhiên sang SQL và tóm tắt kết quả phản hồi |
| **Frontend** | HTML5, Tailwind CSS, Leaflet.js | Giao diện trò chuyện và bản đồ tương tác hiển thị GeoJSON |

---

## 🗄️ Cấu trúc Cơ sở dữ liệu (7 Lớp chuyên đề)

1. **`adm_tinh`**: Ranh giới hành chính Thành phố Hà Nội (`MultiPolygon`).
2. **`adm_ward`**: Ranh giới 121 xã, phường, thị trấn chuẩn sáp nhập hành chính (`MultiPolygon`).
3. **`traffic`**: Mạng lưới đường bộ và đường sắt kèm Topology pgRouting (`source`, `target`, `cost`, `reverse_cost`).
4. **`building`**: Tòa nhà, công trình kiến trúc và thông tin tiện ích công cộng (`MultiPolygon`).
5. **`water_body`**: Hệ thống thủy văn (sông, suối, ao, hồ) kèm diện tích `area_m2` và trọng tâm `centroid_geom`.
6. **`poi`**: Các điểm tiện ích quan tâm (trường học, bệnh viện, nhà ga, điểm du lịch...) dạng `Point`.
7. **`landuse_area`**: Khu vực quy hoạch sử dụng đất (công viên, mảng xanh, khu dân cư...) (`MultiPolygon`).

---

## Hướng dẫn cài đặt & Khởi chạy

### 1. Yêu cầu môi trường

- Python 3.10 trở lên
- PostgreSQL 16+ đã kích hoạt tiện ích `postgis` và `pgrouting`
- CSDL `hanoi_osm` đã được nạp dữ liệu và tạo bảng

### 2. Cài đặt các thư viện phụ thuộc

```bash
# Kích hoạt môi trường ảo (nếu có)
.\venv\Scripts\activate

# Cài đặt thư viện
pip install -r requirements.txt
```

### 3. Khởi chạy ứng dụng

Chạy trực tiếp bằng Python:

```bash
python app.py
```

Hoặc nhấp đúp vào file **`run_app.bat`**.

Truy cập ứng dụng tại trình duyệt web:
**`http://localhost:8000`**

---

## Cấu trúc thư mục dự án

```text
.
├── static/              # Giao diện Web Frontend 
├── venv/                # Môi trường ảo Python 
├── .env                 # Biến môi trường & API Key 
├── .gitignore           # Cấu hình bỏ qua các file không cần thiết
├── app.py               # Máy chủ Backend FastAPI
├── config.py            # Quản lý cấu hình tập trung
├── database.py          # Kết nối CSDL PostgreSQL/PostGIS và thực thi SQL
├── llm.py               # AI Text-to-SQL Engine và quản lý Context
├── requirements.txt     # Danh sách thư viện Python
├── run_app.bat          # File thực thi khởi động nhanh hệ thống
└── README.md            # Tài liệu hướng dẫn sử dụng dự án
```
