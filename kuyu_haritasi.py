# -*- coding: utf-8 -*-
"""Kuyu haritası: tarla sınırı + tüm sondaj noktaları uydu üzerinde.

Renk kodu:
  mavi   = sulu kuyu
  kırmızı = kuru kuyu
  turuncu = mağara/boşluk
Tıklanan yerin koordinatı 6 ondalık basamakla gösterilir.
"""
import json
import math
from pathlib import Path

import folium

from tahmin_motoru import DATA

CIKTI = Path(__file__).parent / "kuyu_haritasi.html"

koseler = json.loads((DATA / "tarla_siniri.json").read_text(encoding="utf-8"))["koseler"]
kuyular = json.loads((DATA / "kuyular.json").read_text(encoding="utf-8"))["kuyular"]

sinir = [(k["enlem"], k["boylam"]) for k in koseler]
merkez_lat = sum(p[0] for p in sinir) / len(sinir)
merkez_lon = sum(p[1] for p in sinir) / len(sinir)

m = folium.Map(location=(merkez_lat, merkez_lon), zoom_start=16, max_zoom=21, tiles=None)

folium.TileLayer(
    tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
    attr="Google Satellite", name="Google Uydu",
    max_zoom=21, max_native_zoom=19,
).add_to(m)
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri World Imagery", name="Esri Uydu",
    max_zoom=21, max_native_zoom=17,
).add_to(m)
folium.LayerControl(collapsed=False).add_to(m)

folium.Polygon(
    sinir, color="yellow", weight=3,
    fill=True, fill_color="yellow", fill_opacity=0.05,
    tooltip="Tarla sınırı (~103 dönüm)",
).add_to(m)

RENK = {
    "sulu": "blue",
    "kuru": "red",
    "magara": "orange",
    "dis_sulu": "green",
    "dis_kurumus": "lightgray",
}
IKON = {
    "sulu": "tint",
    "kuru": "remove",
    "magara": "warning-sign",
    "dis_sulu": "tint",
    "dis_kurumus": "minus",
}

# Birbirine cok yakin dusen isaretleri gorunur kilmak icin ufak gorsel kaydirma
# (~8 m dogu yonune). Veri dosyasindaki koordinatlar degismez.
LAT_M = 111_320.0
LON_M = 111_320.0 * math.cos(math.radians(merkez_lat))
CAKISMA_ESIGI_M = 15.0

yerlesenler = []
for k in kuyular:
    kaydir = sum(
        1
        for y in yerlesenler
        if math.hypot(
            (k["boylam"] - y["boylam"]) * LON_M, (k["enlem"] - y["enlem"]) * LAT_M
        )
        < CAKISMA_ESIGI_M
    )
    k["_g_enlem"] = k["enlem"]
    k["_g_boylam"] = k["boylam"] + kaydir * 0.00009
    yerlesenler.append(k)

for k in kuyular:
    satirlar = [f"<b>{k['isim']}</b> ({k['tip']})"]
    for alan, etiket in [
        ("toplam_derinlik_m", "Derinlik (m)"),
        ("derinlik_araligi_m", "Derinlik aralığı (m)"),
        ("ilk_suya_girilen_derinlik_m", "Suya girilen derinlik (m)"),
        ("magara_girilen_derinlik_m", "Boşluğa girilen derinlik (m)"),
        ("verim", "Verim"),
        ("pompa", "Pompa"),
        ("boru", "Boru"),
        ("durum", "Durum"),
        ("acilis", "Açılış"),
        ("sondaj_notlari", "Not"),
        ("veri_kalitesi_uyarisi", "⚠ UYARI"),
    ]:
        if k.get(alan):
            satirlar.append(f"{etiket}: {k[alan]}")
    popup = folium.Popup("<br>".join(satirlar), max_width=320)

    # Konumu tahmini olan noktalar icin belirsizlik cemberi
    if k.get("konum_belirsizlik_m"):
        folium.Circle(
            (k["enlem"], k["boylam"]),
            radius=k["konum_belirsizlik_m"],
            color=RENK.get(k["tip"], "gray"),
            weight=2, dash_array="6", fill=True, fill_opacity=0.12,
            tooltip=f"{k['isim']} — tahmini konum, ±{k['konum_belirsizlik_m']} m belirsizlik",
        ).add_to(m)

    folium.Marker(
        (k["_g_enlem"], k["_g_boylam"]),
        tooltip=f"{k['isim']} — {k['tip']}"
        + (" (TAHMİNİ KONUM)" if k.get("konum_kalitesi") == "tahmini" else ""),
        popup=popup,
        icon=folium.Icon(
            color=RENK.get(k["tip"], "gray"),
            icon=IKON.get(k["tip"], "question-sign"),
        ),
    ).add_to(m)

# Dogrulanmis koku testi baglantilari (tracer test) — kanal dogrultusu kaniti
baglantilar = json.loads((DATA / "baglantilar.json").read_text(encoding="utf-8"))["testler"]
konum = {k["isim"]: (k["enlem"], k["boylam"]) for k in kuyular}
for t in baglantilar:
    kaynak = t["ilac_dokulen_kuyu"]
    for hedef in t["koku_gelen_kuyular"]:
        if kaynak in konum and hedef in konum:
            folium.PolyLine(
                [konum[kaynak], konum[hedef]],
                color="cyan", weight=4, opacity=0.9,
                tooltip=f"Koku testi bağlantısı: {kaynak} → {hedef} (aynı kanal sistemi)",
            ).add_to(m)

m.add_child(folium.LatLngPopup())
m.save(CIKTI)

html = CIKTI.read_text(encoding="utf-8")
CIKTI.write_text(html.replace(".toFixed(4)", ".toFixed(6)"), encoding="utf-8")

# Kuyular arasi mesafe matrisi (kontrol icin)
print("Kuyular arasi mesafeler (m):")
for i, a in enumerate(kuyular):
    for b in kuyular[i + 1:]:
        dx = (a["boylam"] - b["boylam"]) * LON_M
        dy = (a["enlem"] - b["enlem"]) * LAT_M
        print(f"  {a['isim']}-{b['isim']}: {math.hypot(dx, dy):6.1f}")
print(f"\nHarita yazildi: {CIKTI}")
