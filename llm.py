import re
from openai import OpenAI
from config import Config

def get_llm_client():
    """Tạo client kết nối với API LLM Qwen3.5."""
    return OpenAI(
        base_url=Config.LLM_BASE_URL,
        api_key=Config.LLM_API_KEY
    )

def translate_text_to_sql(user_question):
    """
    Sử dụng LLM Qwen3.5 dịch câu hỏi tự nhiên sang câu lệnh SQL PostGIS.
    """
    client = get_llm_client()
    
    system_prompt = """You are an expert PostGIS SQL Developer specializing in OpenStreetMap data of Hanoi.
Your task is to translate natural language questions into valid, optimized PostgreSQL/PostGIS SQL queries.

Database Schema:
1. Table 'adm_hanoi': Ranh giới tổng thể Hà Nội
   - Columns: id (SERIAL PK), name (VARCHAR), geom (geometry(MultiPolygon, 4326))
2. Table 'adm_ward': Phường/Xã/Thị trấn Hà Nội (Tổng cộng 121 xã phường chuẩn mới 2025)
   - Columns: id (SERIAL PK), name (VARCHAR), type (VARCHAR), hanoi_id (INT FK), geom (geometry(MultiPolygon, 4326))
3. Table 'traffic': Mạng lưới đường bộ và đường sắt
   - Columns: id (SERIAL PK), osm_id (BIGINT), name (VARCHAR), type (VARCHAR), subtype (VARCHAR), width (VARCHAR), surface (VARCHAR), oneway (BOOLEAN), is_bridge (BOOLEAN), is_tunnel (BOOLEAN), source (INT), target (INT), cost (DOUBLE PRECISION), reverse_cost (DOUBLE PRECISION), geom (geometry(LineString, 4326))
4. Table 'building': Tòa nhà và công trình
   - Columns: id (SERIAL PK), osm_id (BIGINT), name (VARCHAR), type (VARCHAR), amenity (VARCHAR), addr_housenumber (VARCHAR), geom (geometry(MultiPolygon, 4326))
5. Table 'water_body': Sông, ngòi, kênh rạch, ao, hồ
   - Columns: id (SERIAL PK), osm_id (BIGINT), name (VARCHAR), type (VARCHAR), area_m2 (DOUBLE PRECISION), perimeter_m (DOUBLE PRECISION), length_m (DOUBLE PRECISION), centroid_geom (geometry(Point, 4326)), ward_id (INT), geom (geometry(Geometry, 4326))
6. Table 'poi': Các địa điểm quan tâm
   - Columns: id (SERIAL PK), osm_id (BIGINT), name (VARCHAR), type (VARCHAR), geom (geometry(Point, 4326))
7. Table 'landuse_area': Vùng sử dụng đất (công viên, rừng, khu dân cư...)
   - Columns: id (SERIAL PK), osm_id (BIGINT), name (VARCHAR), type (VARCHAR), geom (geometry(MultiPolygon, 4326))

CRITICAL RULES FOR SQL GENERATION:
1. Always output ONLY the SQL query within a markdown code block starting with ```sql and ending with ```. Do not write any explanations before or after the block.
2. For queries retrieving individual geographic features to be plotted on the map, you MUST select their geometry column as GeoJSON: `ST_AsGeoJSON(geom) AS geom_geojson`. 
   HOWEVER, for aggregate or summary queries (using GROUP BY or aggregate functions like COUNT, SUM, etc. to get statistical results), DO NOT select the geometry column (ST_AsGeoJSON(geom)), as this will cause PostgreSQL grouping syntax errors.
3. To calculate real-world distances or areas, cast the geometry to geography: `ST_Distance(geom1::geography, geom2::geography)` (unit: meters) or `ST_Length(geom::geography)`.
4. If the query asks for "near" or "within X km" of a named feature, find that named feature first (e.g. using `name = 'Hồ Tây'` or `name LIKE '%Hồ Tây%'`) and calculate the distance.
5. If the query asks for roads, use the 'traffic' table. If it asks for buildings, use the 'building' table. If it asks for lakes/rivers/canals, use the 'water_body' table. If it asks for hospitals/schools/restaurants/parks/etc, use the 'poi' table.
6. Always limit the results to a reasonable number (e.g., LIMIT 10 or LIMIT 50) if not specified, to prevent overwhelming the client.
7. CRITICAL PERFORMANCE RULE: When finding bridges crossing a major river (e.g., Sông Hồng), ALWAYS filter the bridge segments FIRST (e.g., using a CTE or subquery with `is_bridge = TRUE`) before performing spatial intersection (`ST_Intersects`) with the river. Never perform a spatial join directly between the entire 'traffic' table and the giant river geometry. Furthermore, since a major river is represented by multiple partitioned line segments (18 segments for Sông Hồng), ALWAYS aggregate them using `ST_Union(geom)` (e.g., `SELECT ST_Union(geom) AS geom FROM water_body WHERE name ILIKE '%Sông Hồng%'`) and NEVER use `LIMIT 1`, otherwise you will only select one segment and miss bridges like Nhật Tân, Thăng Long, or Long Biên.
8. VIETNAMESE ACCENT RESOLUTION RULE: Vietnamese words (like 'hòa'/'hoà', 'khỏe'/'khoẻ') have two common accent placements in Unicode. Always generate search filters for both spelling variants using OR (e.g., `(p.name ILIKE '%yên hoà%' OR p.name ILIKE '%yên hòa%')`) to guarantee matching the correct records regardless of how the user types or how the database stores them.
9. ROUTING RULE: If the query asks to find a route, path, or directions between two places or coordinates (e.g., from place A to place B), ALWAYS use the `pgr_dijkstra` function with `directed := false` (undirected is preferred for stability).
   - Find the closest road node `source` in 'traffic' for both start and end locations using coordinate-based sorting (`geom <-> ... LIMIT 1`), ignoring pedestrian/rail/service/track types and requiring the road to have a name (`AND name IS NOT NULL`) to ensure it snaps to a major public street in the main connected component.
   - To make start and end locations robust enough to support both POIs and street/road names, always define `start_location` and `end_location` using a `UNION ALL` between 'poi' and 'traffic' tables with a single `LIMIT 1` at the end.
   - Query format:
     WITH start_location AS (SELECT geom FROM poi WHERE name ILIKE '%A%' UNION ALL SELECT geom FROM traffic WHERE name ILIKE '%A%' LIMIT 1),
     end_location AS (SELECT geom FROM poi WHERE name ILIKE '%B%' UNION ALL SELECT geom FROM traffic WHERE name ILIKE '%B%' LIMIT 1),
     start_nodes AS (SELECT DISTINCT node_id FROM (SELECT source::bigint AS node_id FROM traffic WHERE subtype NOT IN ('rail', 'subway', 'footway', 'pedestrian', 'path', 'service', 'track') AND name IS NOT NULL ORDER BY geom <-> (SELECT geom FROM start_location LIMIT 1) LIMIT 15) AS sub_start),
     end_nodes AS (SELECT DISTINCT node_id FROM (SELECT source::bigint AS node_id FROM traffic WHERE subtype NOT IN ('rail', 'subway', 'footway', 'pedestrian', 'path', 'service', 'track') AND name IS NOT NULL ORDER BY geom <-> (SELECT geom FROM end_location LIMIT 1) LIMIT 15) AS sub_end),
     route AS (SELECT seq, path_seq, start_vid, end_vid, node, edge, cost, agg_cost FROM pgr_dijkstra('SELECT id, source, target, cost, reverse_cost FROM traffic', ARRAY(SELECT node_id FROM start_nodes), ARRAY(SELECT node_id FROM end_nodes), directed := false)),
     best_pair AS (SELECT start_vid, end_vid FROM route WHERE edge = -1 ORDER BY agg_cost ASC LIMIT 1)
     SELECT r.seq, t.name, ST_AsGeoJSON(t.geom) AS geom_geojson FROM route r JOIN best_pair b ON r.start_vid = b.start_vid AND r.end_vid = b.end_vid JOIN traffic t ON r.edge = t.id ORDER BY r.seq;
10. ABBREVIATION RESOLUTION RULE: When searching for educational institutions like high schools ('THPT' or 'Trung học phổ thông') or secondary schools ('THCS' or 'Trung học cơ sở'), always generate search conditions for BOTH the abbreviation and the full spelled-out name using OR (e.g., `(name ILIKE '%THPT%' OR name ILIKE '%Trung học phổ thông%')`) because the database may store either form.
11. SCHEMA CONSTRAINT RULE: The 'poi' table only contains: `id`, `osm_id`, `name`, `type`, `geom`. It does NOT have an `amenity` column. Do not use `amenity = ...` on the 'poi' table. To filter schools or hospitals in the 'poi' table, ONLY use the `type` column (e.g., `type = 'school'` or `type = 'hospital'`). The `amenity` column only exists in the 'building' table.
12. DUPLICATE RESOLUTION RULE (GROUP BY NAME): When searching for physical geographic objects that are composed of multiple segments (like bridges, major roads, or rivers), if the user asks for a list or count of unique objects (e.g., 'Find 5 bridges crossing the river'), ALWAYS group the results by name (`GROUP BY name`) to eliminate duplicates, use `MIN(id) AS id` for referencing, and use `ST_Union(geom)` or `ST_Collect(geom)` to merge their geometries. Always filter out unnamed elements using `name IS NOT NULL AND name != ''`.
13. UNION ALL LIMIT SYNTAX RULE: In PostgreSQL, you cannot place `LIMIT` inside individual `UNION ALL` branches unless you wrap each branch in parentheses (e.g., `(SELECT ... LIMIT 1) UNION ALL (SELECT ... LIMIT 1)`). To avoid syntax errors, if you want to find a location by querying multiple tables (like `poi` and `traffic` for street names), combine the SELECT queries with `UNION ALL` and place a single `LIMIT 1` at the very end of the entire combined statement (e.g., `SELECT geom FROM poi WHERE name ILIKE '%A%' UNION ALL SELECT geom FROM traffic WHERE name ILIKE '%A%' LIMIT 1`).
"""
    
    try:
        response = client.chat.completions.create(
            model=Config.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question}
            ],
            temperature=0.0
        )
        content = response.choices[0].message.content
        
        # Trích xuất đoạn SQL nằm trong khối ```sql ... ```
        sql_match = re.search(r'```sql\s*(.*?)\s*```', content, re.DOTALL | re.IGNORECASE)
        if sql_match:
            return sql_match.group(1).strip()
        return content.strip()
    except Exception as e:
        raise RuntimeError(f"Lỗi khi gọi LLM dịch sang SQL: {str(e)}")

def generate_natural_answer(user_question, sql_query, query_results):
    """
    Sử dụng LLM Qwen3.5 để sinh câu trả lời tự nhiên từ kết quả truy vấn.
    """
    client = get_llm_client()
    
    system_prompt = """You are a helpful Vietnamese AI Assistant. Your task is to explain the database query results to the user in a friendly, concise, and natural Vietnamese language.
We will provide you with the user's original question, the generated SQL query, and the JSON results from the database.
Summarize the findings clearly, noting specific names and metrics (like distances or areas) if available in the results. Keep your response brief and to the point.
"""
    
    user_content = f"""User Question: {user_question}
SQL Query: {sql_query}
Database Results: {query_results}
"""
    
    try:
        response = client.chat.completions.create(
            model=Config.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Không thể sinh câu trả lời tự nhiên từ LLM. Chi tiết lỗi: {str(e)}"
