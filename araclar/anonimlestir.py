# -*- coding: utf-8 -*-
"""Gerçek veriyi anonimleştirip paylaşılabilir örnek veri üretir.

Neden
-----
`data/` klasöründe tarlanın ve kuyuların gerçek GPS koordinatları var. Bunlar
özel mülkün ve komşulara ait kuyuların yerini açık eder; herkese açık bir
depoda paylaşılamaz. Ama yöntemin tekrarlanabilir olması için **göreli
geometrinin** korunması gerekir: kuyular arası mesafeler ve yönler analizin
kendisidir.

Yöntem
------
1. Tarla sınırının ağırlık merkezi orijin kabul edilir.
2. Her nokta yerel metre düzlemine taşınır (x: doğu, y: kuzey).
3. Bu metreler, **hayali bir orijin olan 0°N 0°E** etrafında tekrar enlem/boylam
   yapılır. Ekvatorda cos(enlem)=1 olduğu için metrik mesafeler birebir korunur.

Sonuç: kuyular arası tüm mesafe ve açılar aynı kalır, gerçek konum tamamen
kaybolur. 0°N 0°E Atlas Okyanusu'nda bir noktadır — veri bu yüzden bariz
şekilde sentetiktir, kimsenin arazisini işaret etmez.

Ayrıca metin alanlarındaki koordinat kalıntıları ve yer adları temizlenir.

Çalıştır: python araclar/anonimlestir.py
Girdi:    data/*.json   (paylaşılmaz)
Çıktı:    ornek_veri/*.json  (paylaşılır)
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
GERCEK = KOK / "data"
ORNEK = KOK / "ornek_veri"

LAT_M = 111_320.0

# Metin alanlarindan temizlenecek kaliplar
ONDALIK_KOORDINAT = re.compile(r"\b\d{1,3}\.\d{4,}\b")
DMS_KOORDINAT = re.compile(r"\d{1,3}\s*[d°]\s*\d{1,2}'\s*[\d.]+\"?\s*[NSEW]", re.I)

# Temizlenecek yer adlari burada YAZILI DEGILDIR: listenin kendisi konumu ele
# verirdi. Terimler, depoya dahil edilmeyen (.gitignore'da) bir dosyadan
# okunur; her satir bir terimdir. Dosya yoksa sadece koordinat temizligi yapilir.
GIZLI_TERIM_DOSYASI = Path(__file__).resolve().parent / "gizli_terimler.txt"


def gizli_terimler() -> re.Pattern | None:
    if not GIZLI_TERIM_DOSYASI.exists():
        return None
    terimler = [s.strip() for s in
                GIZLI_TERIM_DOSYASI.read_text("utf-8").splitlines() if s.strip()]
    if not terimler:
        return None
    return re.compile(r"\b(" + "|".join(re.escape(t) for t in terimler) + r")\b",
                      re.I)


_GIZLI = gizli_terimler()


def metni_temizle(s: str) -> str:
    s = DMS_KOORDINAT.sub("[koordinat kaldırıldı]", s)
    s = ONDALIK_KOORDINAT.sub("[koordinat kaldırıldı]", s)
    if _GIZLI:
        s = _GIZLI.sub("[yer adı kaldırıldı]", s)
    return s


def agaci_temizle(nesne):
    """JSON ağacındaki tüm metinleri özyinelemeli temizler."""
    if isinstance(nesne, dict):
        return {k: agaci_temizle(v) for k, v in nesne.items()}
    if isinstance(nesne, list):
        return [agaci_temizle(v) for v in nesne]
    if isinstance(nesne, str):
        return metni_temizle(nesne)
    return nesne


def main() -> None:
    sinir = json.loads((GERCEK / "tarla_siniri.json").read_text("utf-8"))
    koseler = sinir["koseler"]

    lat0 = sum(k["enlem"] for k in koseler) / len(koseler)
    lon0 = sum(k["boylam"] for k in koseler) / len(koseler)
    lon_m = LAT_M * math.cos(math.radians(lat0))

    def donustur(enlem: float, boylam: float) -> tuple[float, float]:
        x = (boylam - lon0) * lon_m      # dogu, metre
        y = (enlem - lat0) * LAT_M       # kuzey, metre
        # Hayali orijin 0,0 — ekvatorda oldugu icin metrik olcek korunur
        return (round(y / LAT_M, 7), round(x / LAT_M, 7))

    ORNEK.mkdir(exist_ok=True)
    sayac = 0

    for dosya in sorted(GERCEK.glob("*.json")):
        veri = json.loads(dosya.read_text("utf-8"))
        veri = agaci_temizle(veri)

        def noktalari_tasi(nesne):
            nonlocal sayac
            if isinstance(nesne, dict):
                if "enlem" in nesne and "boylam" in nesne and \
                        isinstance(nesne["enlem"], (int, float)):
                    nesne["enlem"], nesne["boylam"] = donustur(
                        nesne["enlem"], nesne["boylam"])
                    sayac += 1
                return {k: noktalari_tasi(v) for k, v in nesne.items()}
            if isinstance(nesne, list):
                return [noktalari_tasi(v) for v in nesne]
            return nesne

        veri = noktalari_tasi(veri)
        veri["_ANONIM"] = ("Koordinatlar anonimlestirildi: goreli geometri "
                           "korundu, gercek konum kaldirildi. "
                           "Bkz. araclar/anonimlestir.py")
        (ORNEK / dosya.name).write_text(
            json.dumps(veri, ensure_ascii=False, indent=2), "utf-8")
        print(f"  {dosya.name} -> ornek_veri/{dosya.name}")

    print(f"\n{sayac} koordinat anonimlestirildi.")
    print(f"Hayali orijin: 0.0 N, 0.0 E (metrik olcek korunur)")


if __name__ == "__main__":
    main()
