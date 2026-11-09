"""Copy the notebook's exported tables into the website's data/ folder and build a light-weight
community-district map layer.

Usage:
    python scripts/prepare_data.py <notebook_output_folder>

<notebook_output_folder> is the folder the notebook writes (outputs/ next to the notebook). The
website never re-cleans anything: it reads the integrated district/year table and the hourly crash
table exactly as the notebook exported them, so every number on the site matches the notebook.
"""
import csv
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data"
BOROUGH_ABBR = {1: "MN", 2: "BX", 3: "BK", 4: "QN", 5: "SI"}
SIMPLIFY_TOLERANCE = 0.0002   # degrees (about 20 m): invisible at city zoom, shrinks the file ~10x
COORD_DECIMALS = 5


def perpendicular_distance(point, start, end):
    """Distance from point to the line through start and end (planar, fine at city scale)."""
    (x, y), (x1, y1), (x2, y2) = point, start, end
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
    return abs(dy * x - dx * y + x2 * y1 - y2 * x1) / (dx * dx + dy * dy) ** 0.5


def simplify_ring(ring, tolerance=SIMPLIFY_TOLERANCE):
    """Ramer-Douglas-Peucker simplification (iterative, so long rings cannot hit recursion limits).
    The ring stays closed and keeps at least 4 points so it remains a valid polygon."""
    if len(ring) <= 4:
        return ring
    keep = [False] * len(ring)
    keep[0] = keep[-1] = True
    stack = [(0, len(ring) - 1)]
    while stack:
        first, last = stack.pop()
        best, index = 0.0, None
        for i in range(first + 1, last):
            d = perpendicular_distance(ring[i], ring[first], ring[last])
            if d > best:
                best, index = d, i
        if index is not None and best > tolerance:
            keep[index] = True
            stack += [(first, index), (index, last)]
    out = [[round(x, COORD_DECIMALS), round(y, COORD_DECIMALS)] for (x, y), k in zip(ring, keep) if k]
    return out if len(out) >= 4 else ring


def ring_area_centroid(ring):
    """Signed area and centroid of one closed ring (shoelace formula)."""
    area = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        cross = x1 * y2 - x2 * y1
        area += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    area /= 2
    return area, (cx / (6 * area), cy / (6 * area)) if area else ring[0]


def main(source):
    source = Path(source)
    OUT.mkdir(exist_ok=True)
    for name in ["integrated_district_year.csv", "crashes_district_year_hour.csv"]:
        shutil.copyfile(source / "data" / name, OUT / name)

    with open(source / "data" / "integrated_district_year.csv", encoding="utf-8") as f:
        districts = sorted({(int(r["cd"]), r["borough"]) for r in csv.DictReader(f)})
    regular = {cd for cd, _ in districts}

    geo = json.load(open(source / "reference" / "community_districts_26b.geojson", encoding="utf-8"))
    features, centroids = [], {}
    for feature in geo["features"]:
        cd = int(feature["properties"]["boro_cd"])
        if cd not in regular:          # parks, airports and other joint interest areas have no data
            continue
        polygons = feature["geometry"]["coordinates"]
        if feature["geometry"]["type"] == "Polygon":
            polygons = [polygons]
        simplified = [[simplify_ring(ring) for ring in polygon] for polygon in polygons]
        # Label point = centroid of the largest outer ring (keeps the bubble on land for
        # districts made of several islands).
        largest = max((ring_area_centroid(p[0]) for p in polygons), key=lambda ac: abs(ac[0]))
        centroids[cd] = largest[1]
        features.append({"type": "Feature", "id": str(cd), "properties": {"boro_cd": str(cd)},
                         "geometry": {"type": "MultiPolygon", "coordinates": simplified}})
    assert len(features) == len(regular) == 59, (len(features), len(regular))
    with open(OUT / "community_districts.geojson", "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, separators=(",", ":"))

    with open(OUT / "districts.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["cd", "borough", "label", "lon", "lat"])
        for cd, borough in districts:
            lon, lat = centroids[cd]
            writer.writerow([cd, borough, f"{BOROUGH_ABBR[cd // 100]} {cd % 100:02d}", round(lon, 5), round(lat, 5)])
    for path in sorted(OUT.iterdir()):
        print(f"{path.name:40} {path.stat().st_size / 1024:8.1f} KB")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
