import mysql.connector
from shapely.geometry import Point, Polygon
from h3 import h3
from collections import defaultdict
from nyc_polygon import NYC_POLYGON
import folium

H3_RESOLUTION = 7
FIXED_ZOOM = 12
# ============================================================
# 2. Database
# ============================================================
def fetch_points(table, start_ts, end_ts):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root@123",
        database="taxiProduction",
    )
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        f"""
        SELECT lat, lon
        FROM {table}
        WHERE activity_at BETWEEN %s AND %s
        """,
        (start_ts, end_ts),
    )
    rows = cursor.fetchall()

    cursor.close()
    conn.close()
    return rows

# ============================================================
# 3. Filter + H3 aggregation
# ============================================================
def prepare_points(rows):
    points = []
    hex_counts = defaultdict(int)

    for r in rows:
        pt = Point(r["lon"], r["lat"])
        if NYC_POLYGON.contains(pt):
            points.append([r["lat"], r["lon"], 1])
            h = h3.geo_to_h3(r["lat"], r["lon"], H3_RESOLUTION)
            hex_counts[h] += 1

    return points, hex_counts

# ============================================================
# 4. Map creation
# ============================================================
def create_map(all_points):
    center_lat = sum(p[0] for p in all_points) / len(all_points)
    center_lon = sum(p[1] for p in all_points) / len(all_points)

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,   # initial zoom
        min_zoom=10,     # optional
        max_zoom=13,     # 🚫 cannot zoom beyond 13
        tiles="CartoDB Positron",
    )

    return m
