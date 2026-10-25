# -*- coding: utf-8 -*-
"""Tarla sınırı kontrol haritası.

Sınır köşelerini uydu görüntüsü üzerinde kapalı poligon olarak gösterir,
alanı hesaplar (dönüm doğrulaması). Haritada tıklanan yerin koordinatı
6 ondalık basamakla (~11 cm çözünürlük) gösterilir — kuyu konumları
bu hassasiyetle toplanacak.

Katmanlar: Google Uydu (varsayılan) ve Esri World Imagery.
max_native_zoom sayesinde karo bulunmayan yakınlaştırma seviyelerinde
görüntü büyütülerek gösterilir ("map data not available" çıkmaz).
"""
import json
import math
from pathlib import Path

import folium

from tahmin_motoru import DATA

VERI = DATA / "tarla_siniri.json"
CIKTI = Path(__file__).parent / "sinir_kontrol.html"

koseler = json.loads(VERI.read_text(encoding="utf-8"))["koseler"]
noktalar = [(k["enlem"], k["boylam"], k["etiket"]) for k in koseler]

merkez_lat = sum(p[0] for p in noktalar) / len(noktalar)
merkez_lon = sum(p[1] for p in noktalar) / len(noktalar)

# Alan hesabı (shoelace, yerel metre düzlemi)
LAT_M = 111_320.0
LON_M = 111_320.0 * math.cos(math.radians(merkez_lat))
xy = [((p[1] - merkez_lon) * LON_M, (p[0] - merkez_lat) * LAT_M) for p in noktalar]
alan_m2 = abs(
    sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(xy, xy[1:] + xy[:1]))
) / 2.0
alan_donum = alan_m2 / 1000.0

m = folium.Map(location=(merkez_lat, merkez_lon), zoom_start=16, max_zoom=21, tiles=None)

folium.TileLayer(
    tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
    attr="Google Satellite",
    name="Google Uydu",
    max_zoom=21,
    max_native_zoom=19,
).add_to(m)

folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri World Imagery",
    name="Esri Uydu",
    max_zoom=21,
    max_native_zoom=17,
).add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

folium.Polygon(
    [(p[0], p[1]) for p in noktalar],
    color="yellow",
    weight=3,
    fill=True,
    fill_color="yellow",
    fill_opacity=0.08,
    tooltip=f"Tarla sınırı — {alan_donum:.1f} dönüm",
).add_to(m)

for enlem, boylam, etiket in noktalar:
    folium.CircleMarker(
        (enlem, boylam),
        radius=5,
        color="red",
        fill=True,
        fill_opacity=1,
        tooltip=f"{etiket}: {enlem:.6f}, {boylam:.6f}",
    ).add_to(m)

# Tıklanan yerin koordinatını gösteren popup
m.add_child(folium.LatLngPopup())

m.save(CIKTI)

# folium LatLngPopup 4 ondalık gösterir; kuyu konumları için 6 basamağa çıkar
html = CIKTI.read_text(encoding="utf-8")
CIKTI.write_text(html.replace(".toFixed(4)", ".toFixed(6)"), encoding="utf-8")

print(f"Harita yazildi: {CIKTI}")
print(f"Poligon alani: {alan_m2:,.0f} m2 = {alan_donum:.1f} donum")
