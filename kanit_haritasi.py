# -*- coding: utf-8 -*-
"""Kanıt haritası: sadece doğrudan gözlemleri gösterir, tahmin üretmez.

`dogrulama.py` mekânsal tahmin modelinin bu veriyle geçerli olmadığını
gösterdi (permütasyon testi p ≈ 0.45). Bu yüzden burada düzgün geçişli bir
"potansiyel" yüzeyi ÜRETİLMEZ. Bunun yerine her sondaj noktasının etrafında
40 m'lik bir kanıt yarıçapı çizilir — yani "bu alan hakkında doğrudan
gözlemimiz var" der, "burada su vardır" demez.

40 m neden: tarlada 47-49 m arayla sulu/kuru çiftler gözlendi (K3-K4, K1-K2).
Yani gözlemin geçerliliği bu mesafenin altında kalır.

Çalıştır: python kanit_haritasi.py
Çıktı:    kanit_haritasi.html
"""
import json
from pathlib import Path

import folium

from tahmin_motoru import Model

KOK = Path(__file__).parent
CIKTI = KOK / "kanit_haritasi.html"

KANIT_YARICAP_M = 40
MAGARA_RISK_M = 70
DERIN_ESIK_M = 100      # bu derinligin altinda kalan kuru kuyular "eksik test"

model = Model()
merkez = model.xy2ll(0, 0)

m = folium.Map(location=merkez, zoom_start=16, max_zoom=21, tiles=None)
folium.TileLayer(
    tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
    attr="Google Satellite", name="Google Uydu", max_zoom=21, max_native_zoom=19,
).add_to(m)
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri World Imagery", name="Esri Uydu", max_zoom=21, max_native_zoom=17,
).add_to(m)

folium.Polygon(
    [(k["enlem"], k["boylam"]) for k in model.sinir],
    color="yellow", weight=3, fill=False, tooltip="Tarla sınırı (~103 dönüm)",
).add_to(m)

kanit_verimli = folium.FeatureGroup(name="Kanıt: su bulundu (40 m)", show=True)
kanit_kuru = folium.FeatureGroup(name="Kanıt: kuru çıktı (40 m)", show=True)
derinlestirme = folium.FeatureGroup(name="Derinleştirme adayları", show=True)
risk = folium.FeatureGroup(name="Mağara / sondaj riski", show=True)
isaretler = folium.FeatureGroup(name="Sondaj noktaları", show=True)

for k in model.kuyular:
    ad = k["isim"]
    s = model.skorlar.get(ad, {})
    skor = s.get("verim_skoru", 0)
    derinlik = k.get("toplam_derinlik_m")
    verimli = skor >= 0.5

    if k["tip"] == "magara":
        folium.Circle(
            (k["enlem"], k["boylam"]), radius=MAGARA_RISK_M,
            color="orange", weight=2, dash_array="8",
            fill=True, fill_opacity=0.18,
            tooltip=f"{ad}: 20 m'de boşluk — sondaj riski bölgesi",
        ).add_to(risk)
    else:
        folium.Circle(
            (k["enlem"], k["boylam"]), radius=KANIT_YARICAP_M,
            color="#22aa44" if verimli else "#cc3333", weight=2,
            fill=True, fill_opacity=0.20,
            tooltip=f"{ad}: {'su bulundu' if verimli else 'kuru/zayıf'} "
                    f"— doğrudan gözlem alanı",
        ).add_to(kanit_verimli if verimli else kanit_kuru)

    # Sig birakilmis kuru kuyular: derinlestirme adayi
    if (not verimli and k["tip"] == "kuru" and derinlik and derinlik < DERIN_ESIK_M):
        folium.Circle(
            (k["enlem"], k["boylam"]), radius=18,
            color="#3388ff", weight=3, fill=False,
            tooltip=f"{ad}: sadece {derinlik} m — derinleştirme adayı",
        ).add_to(derinlestirme)

    bilgi = [f"<b>{ad}</b> ({k['tip']})"]
    if derinlik:
        bilgi.append(f"Derinlik: {derinlik} m")
    if k.get("verim"):
        bilgi.append(f"Verim: {k['verim']}")
    if k.get("acilis"):
        bilgi.append(f"Açılış: {k['acilis']}")
    if s.get("gerekce"):
        bilgi.append(f"<i>{s['gerekce']}</i>")
    if k.get("veri_kalitesi_uyarisi"):
        bilgi.append(f"<b>⚠ {k['veri_kalitesi_uyarisi']}</b>")

    RENK = {"sulu": "blue", "kuru": "red", "magara": "orange",
            "dis_sulu": "green", "dis_kurumus": "lightgray"}
    folium.CircleMarker(
        (k["enlem"], k["boylam"]), radius=7, color="white", weight=2,
        fill=True, fill_color=RENK.get(k["tip"], "gray"), fill_opacity=1,
        tooltip=ad, popup=folium.Popup("<br>".join(bilgi), max_width=340),
    ).add_to(isaretler)

for g in (kanit_verimli, kanit_kuru, derinlestirme, risk, isaretler):
    g.add_to(m)

# Koku testi: kanitlanmis hidrolik baglanti
konum = {n.isim: (n.x, n.y) for n in model.noktalar}
for t in model.baglantilar:
    a = t["ilac_dokulen_kuyu"]
    for b in t["koku_gelen_kuyular"]:
        if a in konum and b in konum:
            folium.PolyLine(
                [model.xy2ll(*konum[a]), model.xy2ll(*konum[b])],
                color="cyan", weight=4, opacity=0.9,
                tooltip=f"Kanıtlanmış hidrolik bağlantı: {a} ↔ {b} "
                        f"(koku testi). Aradaki hat sulu demek DEĞİLDİR.",
            ).add_to(m)

aciklama = """
<div style="position:fixed; bottom:18px; left:18px; z-index:9999;
     background:rgba(255,255,255,.94); padding:10px 13px; border-radius:8px;
     font:12px/1.5 sans-serif; max-width:330px; box-shadow:0 2px 8px rgba(0,0,0,.3)">
<b>Kanıt haritası</b><br>
Bu harita tahmin değil, <b>doğrudan gözlem</b> gösterir.<br><br>
<span style="color:#22aa44">●</span> Su bulunan nokta + 40 m kanıt alanı<br>
<span style="color:#cc3333">●</span> Kuru/zayıf nokta + 40 m kanıt alanı<br>
<span style="color:#3388ff">○</span> Sığ bırakılmış kuru kuyu (derinleştirme adayı)<br>
<span style="color:orange">◌</span> Mağara — sondaj riski<br>
<span style="color:#00b7c2">━</span> Koku testiyle kanıtlanmış bağlantı<br><br>
Renksiz alanlar <b>test edilmemiştir</b>. Model doğrulaması, mevcut 13 noktayla
mekânsal tahminin rastgeleden iyi olmadığını gösterdi
(<i>dogrulama_raporu.md</i>).
</div>
"""
m.get_root().html.add_child(folium.Element(aciklama))

folium.LayerControl(collapsed=False).add_to(m)
m.add_child(folium.LatLngPopup())
m.save(CIKTI)
CIKTI.write_text(CIKTI.read_text("utf-8").replace(".toFixed(4)", ".toFixed(6)"), "utf-8")
print(f"Harita yazildi: {CIKTI}")
