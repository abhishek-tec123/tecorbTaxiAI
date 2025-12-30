# group_hexes_connected_map_4groups.py
# ------------------------------------------------
# AUTO-RUN
# Shows 4 connected H3 groups on a Folium map
# ------------------------------------------------

import networkx as nx
from collections import deque
import folium
from shapely.geometry import Polygon
from h3 import h3

# IMPORT DATA FROM AUTO-RUN MODULE
from plot_rider_driver import HEXES, RIDER_COUNTS, DRIVER_COUNTS, NYC_POLYGON

# ------------------------------------------------
# 1. Build adjacency graph
# ------------------------------------------------
hex_set = set(HEXES)
G = nx.Graph()

for h in HEXES:
    G.add_node(h)
    for n in h3.k_ring(h, 1):  # H3 v3 compatible
        if n in hex_set and n != h:
            G.add_edge(h, n)

print(f"Total hexes: {len(G.nodes)}")
print(f"Connected components: {nx.number_connected_components(G)}")

# ------------------------------------------------
# 2. Balanced connected grouping (4 groups, deterministic)
# ------------------------------------------------
def split_connected_balanced(graph, k=4):
    nodes = sorted(graph.nodes)  # deterministic order

    # Pick seeds evenly across the node list
    n = len(nodes)
    step = max(1, n // k)
    seeds = [nodes[i * step] for i in range(k)]

    owner = {}
    groups = {i: set() for i in range(k)}
    queues = [deque() for _ in range(k)]

    for i, h in enumerate(seeds):
        owner[h] = i
        groups[i].add(h)
        queues[i].append(h)

    # BFS growth for each group
    while any(queues):
        for i in range(k):
            if not queues[i]:
                continue
            cur = queues[i].popleft()
            for nbr in sorted(graph.neighbors(cur)):  # deterministic neighbor order
                if nbr not in owner:
                    owner[nbr] = i
                    groups[i].add(nbr)
                    queues[i].append(nbr)

    return groups

groups = split_connected_balanced(G, k=4)

# ------------------------------------------------
# 2b. Print groups and their hex IDs
# ------------------------------------------------
for gid, hexes in sorted(groups.items()):
    print(f"\nGroup {gid + 1} ({len(hexes)} hexes):")
    for h in sorted(hexes):
        print(h)

# ------------------------------------------------
# 3. Create Folium map
# ------------------------------------------------
def center_hexes(hexes):
    lats, lons = [], []
    for h in hexes:
        lat, lon = h3.h3_to_geo(h)
        lats.append(lat)
        lons.append(lon)
    return sum(lats) / len(lats), sum(lons) / len(lons)

center_lat, center_lon = center_hexes(HEXES)
m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=12,
    tiles="CartoDB Positron"
)

# ------------------------------------------------
# 4. Colors for 4 groups
# ------------------------------------------------
COLORS = {
    0: "blue",
    1: "green",
    2: "orange",
    3: "purple",
}

layers = {i: folium.FeatureGroup(name=f"Group {i+1}") for i in range(4)}

# ------------------------------------------------
# 5. Draw hexes by group
# ------------------------------------------------
for gid, hexes in groups.items():
    for h in hexes:
        boundary = h3.h3_to_geo_boundary(h, geo_json=True)
        hex_poly = Polygon([(lon, lat) for lon, lat in boundary])
        clipped = NYC_POLYGON.intersection(hex_poly)

        if clipped.is_empty:
            continue

        polys = [clipped] if clipped.geom_type == "Polygon" else clipped.geoms

        for poly in polys:
            coords = [(lat, lon) for lon, lat in poly.exterior.coords]

            popup = (
                f"<b>Group:</b> {gid + 1}<br>"
                f"<b>Hex:</b> {h}<br>"
                f"<b>Riders:</b> {RIDER_COUNTS.get(h, 0)}<br>"
                f"<b>Drivers:</b> {DRIVER_COUNTS.get(h, 0)}"
            )

            folium.Polygon(
                locations=coords,
                color=COLORS[gid],
                weight=2,
                fill=True,
                fill_color=COLORS[gid],
                fill_opacity=0.45,
                popup=popup,
            ).add_to(layers[gid])

# ------------------------------------------------
# 6. Add layers & save
# ------------------------------------------------
for layer in layers.values():
    m.add_child(layer)

folium.LayerControl(collapsed=False).add_to(m)

m.save("map_4_connected_hex_groups.html")

print("\n✅ Map saved → map_4_connected_hex_groups.html")
print("Open this file in your browser to see the 4 zones.")
