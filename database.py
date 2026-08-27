import psycopg2
from psycopg2.extras import RealDictCursor
import json
from config import Config

def get_db_connection():
    """Tạo kết nối tới cơ sở dữ liệu PostgreSQL."""
    return psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        database=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD
    )

def execute_query(sql_query):
    """
    Thực thi câu lệnh SQL truy vấn không gian.
    Trả về dữ liệu bảng và tự động định dạng các cột hình học thành GeoJSON để vẽ bản đồ.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        
        features = []
        formatted_rows = []
        
        for row in rows:
            row_data = {}
            geojson_geom = None
            
            for key, val in row.items():
                # Tự động nhận diện cột chứa dữ liệu hình học GeoJSON
                if 'geojson' in key.lower() or key.lower() == 'geom':
                    if val:
                        try:
                            # Cột ST_AsGeoJSON trả về chuỗi String, cần parse sang Object JSON
                            geojson_geom = json.loads(val) if isinstance(val, str) else val
                        except Exception:
                            geojson_geom = val
                else:
                    # Lưu các trường dữ liệu thuộc tính thông thường
                    row_data[key] = val
            
            formatted_rows.append(row_data)
            
            # Nếu dòng này chứa hình học, đóng gói thành đối tượng GeoJSON Feature
            if geojson_geom:
                features.append({
                    "type": "Feature",
                    "geometry": geojson_geom,
                    "properties": row_data
                })
        
        feature_collection = {
            "type": "FeatureCollection",
            "features": features
        }
        
        return {
            "success": True,
            "columns": list(formatted_rows[0].keys()) if formatted_rows else [],
            "rows": formatted_rows,
            "geojson": feature_collection,
            "error": None
        }
    except Exception as e:
        if conn:
            conn.rollback()
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "geojson": None,
            "error": str(e)
        }
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
