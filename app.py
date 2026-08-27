import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

# Import các module nội bộ
from database import execute_query
from llm import translate_text_to_sql, generate_natural_answer

# Khởi tạo ứng dụng FastAPI
app = FastAPI(title="Hanoi Text-to-SQL Spatial Map")

# Khai báo cấu trúc dữ liệu gửi lên từ Client
class QuestionRequest(BaseModel):
    question: str

# Khai báo API Endpoint nhận câu hỏi và xử lý
@app.post("/api/ask")
async def ask_question(request: QuestionRequest):
    user_question = request.question.strip()
    if not user_question:
        raise HTTPException(status_code=400, detail="Câu hỏi không được để trống")
    
    try:
        # Bước 1: Dịch câu hỏi tự nhiên sang SQL thông qua LLM Qwen3.5
        sql_query = translate_text_to_sql(user_question)
        
        # Bước 2: Thực thi SQL dưới PostGIS
        db_result = execute_query(sql_query)
        
        if not db_result["success"]:
            # Nếu chạy SQL bị lỗi, trả về lỗi SQL kèm theo câu lệnh đã dịch để debug
            return {
                "success": False,
                "sql": sql_query,
                "answer": f"Đã dịch sang câu lệnh SQL nhưng thực thi gặp lỗi ở cơ sở dữ liệu.",
                "columns": [],
                "rows": [],
                "geojson": None,
                "error": db_result["error"]
            }
            
        # Bước 3: Gửi kết quả truy vấn (tăng giới hạn từ 30 lên 150 dòng để tránh cắt cụt lộ trình dẫn đường) sang LLM để sinh câu trả lời tự nhiên
        sample_results = db_result["rows"][:150]
        natural_answer = generate_natural_answer(user_question, sql_query, sample_results)
        
        return {
            "success": True,
            "sql": sql_query,
            "answer": natural_answer,
            "columns": db_result["columns"],
            "rows": db_result["rows"],
            "geojson": db_result["geojson"],
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "sql": None,
            "answer": f"Đã xảy ra lỗi hệ thống khi xử lý câu hỏi: {str(e)}",
            "columns": [],
            "rows": [],
            "geojson": None,
            "error": str(e)
        }

# Mount thư mục static phục vụ giao diện Web Frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def read_index():
    """Trả về trang chủ index.html."""
    index_path = os.path.join(static_dir, "index.html")
    if not os.path.exists(index_path):
        # Trả về trang thông báo tạm nếu chưa tạo index.html
        return {"message": "Backend đang hoạt động. Vui lòng tạo file index.html trong thư mục static."}
    return FileResponse(index_path)

if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=8000)
