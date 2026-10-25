# -*- coding: utf-8 -*-
"""Yeraltı suyu potansiyeli tahmin motoru.

Yöntem özeti
------------
Karstik arazide su, tabaka halinde değil dar çatlak/kanal sistemlerinde akar.
Bu yüzden düz (izotropik) enterpolasyon yanıltır: tarlada 47-49 m arayla
sulu/kuru kuyu çiftleri var (K3-K4, K1-K2). Model bunu iki şekilde hesaba katar:

1. ANİZOTROPİK ÇEKİRDEK
   Koku testi (K7'ye dökülen kimyasal K3'ten geldi) iki kuyunun aynı kanala
   bağlı olduğunu kanıtlıyor. Bu eksen boyunca bilgi uzağa taşınır (menzil
   ~260 m), eksene dik yönde ise hızla söner (menzil ~55 m). Dik menzil,
   gözlenen sulu/kuru çiftlerinin mesafesinden alındı.

2. DERİNLİĞE GÖRE KANIT GÜCÜ
   Kuru bir kuyu "burada su yok" demez, "kazılan derinliğe kadar su yok" der.
   Tarlada su 30 m (K3) ile 220 m (K7) arasında bulunmuş. 60 m'de bırakılmış
   bir kuyu bu yüzden zayıf negatif kanıttır; skorlar.json'daki `guven` alanı
   bunu taşır.

Tahmin, ağırlıklı kanıt ortalamasının bir ön-değere (prior) doğru
büzüştürülmesiyle üretilir; veri seyrek olan yerlerde sonuç otomatik olarak
ön-değere yaklaşır ve belirsizlik yükselir.

Çıktılar: su potansiyeli yüzeyi, belirsizlik yüzeyi, önerilen sondaj
derinliği yüzeyi ve maliyet-farkındalıklı sondaj noktası önerileri.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import matplotlib
from matplotlib import colors
from matplotlib.path import Path as MplPath

KOK = Path(__file__).parent

# Gercek veri (data/) depoya dahil degildir: tarlanin ve komsu kuyularin
# GPS konumlarini icerir. Yoksa anonimlestirilmis ornek veriye dusulur;
# goreli geometri ayni oldugu icin tum analizler birebir ayni sonucu verir.
_GERCEK = KOK / "data"
DATA = _GERCEK if _GERCEK.exists() else KOK / "ornek_veri"

# --- Model parametreleri -----------------------------------------------------

MENZIL_EKSEN_M = 260.0   # kanal ekseni boyunca etki menzili
MENZIL_DIK_M = 55.0      # eksene dik etki menzili (sulu/kuru cift mesafesinden)
PRIOR = 0.35             # veri yokken varsayilan su olasiligi (7 kuyudan 3'u sulu)
PSEUDO_AGIRLIK = 0.7     # prior'a buzusme gucu
GRID_ADIM_M = 5.0        # harita cozunurlugu

# Oneri kisitlari
MIN_MESAFE_MEVCUT_M = 60.0   # mevcut sondajlara en az bu kadar uzak olsun
MAGARA_KACINMA_M = 70.0      # magara/bosluk cevresinde sondaj riski
ONERILER_ARASI_MIN_M = 90.0  # onerilen noktalar birbirine yapismasin
ONERI_SAYISI = 5

# Derinlik onerisi
MIN_ONERILEN_DERINLIK_M = 120.0  # sig birakilmis kuru kuyulardan ders: erken pes etme
DERINLIK_EMNIYET_PAYI_M = 40.0


@dataclass
class Nokta:
    isim: str
    x: float          # dogu (m)
    y: float          # kuzey (m)
    skor: float       # 0-1 verim
    guven: float      # 0-1 kanit gucu
    tip: str
    su_derinligi: float | None


class Model:
    def __init__(self) -> None:
        self.kuyular = json.loads((DATA / "kuyular.json").read_text("utf-8"))["kuyular"]
        self.sinir = json.loads((DATA / "tarla_siniri.json").read_text("utf-8"))["koseler"]
        self.skorlar = json.loads((DATA / "skorlar.json").read_text("utf-8"))["skorlar"]
        self.baglantilar = json.loads((DATA / "baglantilar.json").read_text("utf-8"))["testler"]

        # Yerel metre duzlemi: tarla merkezi orijin
        self.lat0 = sum(k["enlem"] for k in self.sinir) / len(self.sinir)
        self.lon0 = sum(k["boylam"] for k in self.sinir) / len(self.sinir)
        self.LAT_M = 111_320.0
        self.LON_M = 111_320.0 * math.cos(math.radians(self.lat0))

        self.noktalar = self._noktalari_hazirla()
        self.eksen = self._kanal_ekseni()
        self.sinir_xy = np.array([self.ll2xy(k["enlem"], k["boylam"]) for k in self.sinir])
        self.sinir_yolu = MplPath(self.sinir_xy)

    # --- koordinat donusumleri ---
    def ll2xy(self, lat: float, lon: float) -> tuple[float, float]:
        return ((lon - self.lon0) * self.LON_M, (lat - self.lat0) * self.LAT_M)

    def xy2ll(self, x: float, y: float) -> tuple[float, float]:
        return (y / self.LAT_M + self.lat0, x / self.LON_M + self.lon0)

    # --- veri hazirligi ---
    def _noktalari_hazirla(self) -> list[Nokta]:
        cikti = []
        for k in self.kuyular:
            s = self.skorlar.get(k["isim"])
            if not s:
                continue
            x, y = self.ll2xy(k["enlem"], k["boylam"])
            cikti.append(Nokta(
                isim=k["isim"], x=x, y=y,
                skor=s["verim_skoru"], guven=s["guven"],
                tip=k["tip"], su_derinligi=s.get("su_derinligi_m"),
            ))
        return cikti

    def _kanal_ekseni(self) -> tuple[float, float]:
        """Koku testi bağlantılarından ortalama kanal doğrultusu (birim vektör)."""
        konum = {n.isim: (n.x, n.y) for n in self.noktalar}
        vektorler = []
        for t in self.baglantilar:
            a = t["ilac_dokulen_kuyu"]
            for b in t["koku_gelen_kuyular"]:
                if a in konum and b in konum:
                    dx = konum[b][0] - konum[a][0]
                    dy = konum[b][1] - konum[a][1]
                    n = math.hypot(dx, dy)
                    if n > 1:
                        # yon isaretinden bagimsiz eksen: acinin 2 katiyla ortala
                        aci = math.atan2(dy, dx)
                        vektorler.append((math.cos(2 * aci), math.sin(2 * aci)))
        if not vektorler:
            return (1.0, 0.0)
        cx = sum(v[0] for v in vektorler) / len(vektorler)
        cy = sum(v[1] for v in vektorler) / len(vektorler)
        aci = math.atan2(cy, cx) / 2
        return (math.cos(aci), math.sin(aci))

    # --- cekirdek ---
    def _agirliklar(self, X: np.ndarray, Y: np.ndarray) -> np.ndarray:
        """Her gözlem için grid üzerindeki anizotropik ağırlıklar. (n, ...) dizi."""
        ex, ey = self.eksen
        cikti = []
        for n in self.noktalar:
            dx = X - n.x
            dy = Y - n.y
            d_eksen = dx * ex + dy * ey          # kanal boyunca
            d_dik = -dx * ey + dy * ex           # kanala dik
            u = (d_eksen / MENZIL_EKSEN_M) ** 2 + (d_dik / MENZIL_DIK_M) ** 2
            cikti.append(np.exp(-0.5 * u) * n.guven)
        return np.array(cikti)

    def yuzeyler(self) -> dict:
        """Potansiyel, belirsizlik ve önerilen derinlik yüzeylerini üretir."""
        xs = self.sinir_xy[:, 0]
        ys = self.sinir_xy[:, 1]
        pay = 40.0
        gx = np.arange(xs.min() - pay, xs.max() + pay, GRID_ADIM_M)
        gy = np.arange(ys.min() - pay, ys.max() + pay, GRID_ADIM_M)
        X, Y = np.meshgrid(gx, gy)

        W = self._agirliklar(X, Y)                      # (n, ny, nx)
        S = np.array([n.skor for n in self.noktalar])[:, None, None]

        toplam = W.sum(axis=0)
        potansiyel = (W * S).sum(axis=0) + PSEUDO_AGIRLIK * PRIOR
        potansiyel /= (toplam + PSEUDO_AGIRLIK)

        # Belirsizlik: veri yogunlugu dusukse + yakin gozlemler celisiyorsa yuksek
        guven_orani = toplam / (toplam + PSEUDO_AGIRLIK)
        ort = (W * S).sum(axis=0) / np.maximum(toplam, 1e-9)
        celiski = np.sqrt((W * (S - ort) ** 2).sum(axis=0) / np.maximum(toplam, 1e-9))
        belirsizlik = (1 - guven_orani) * 0.65 + np.clip(celiski / 0.5, 0, 1) * 0.35

        # Onerilen derinlik: su bulunan derinliklerin ayni cekirdekle enterpolasyonu
        derinlikli = [(i, n) for i, n in enumerate(self.noktalar) if n.su_derinligi]
        if derinlikli:
            Wd = np.array([W[i] for i, _ in derinlikli])
            D = np.array([n.su_derinligi for _, n in derinlikli])[:, None, None]
            derinlik = (Wd * D).sum(axis=0) / np.maximum(Wd.sum(axis=0), 1e-9)
            derinlik = np.where(Wd.sum(axis=0) < 0.05, np.nan, derinlik)
        else:
            derinlik = np.full_like(X, np.nan)
        onerilen_derinlik = np.fmax(derinlik + DERINLIK_EMNIYET_PAYI_M,
                                    MIN_ONERILEN_DERINLIK_M)

        icerde = self.sinir_yolu.contains_points(
            np.column_stack([X.ravel(), Y.ravel()])
        ).reshape(X.shape)

        return dict(X=X, Y=Y, gx=gx, gy=gy, potansiyel=potansiyel,
                    belirsizlik=belirsizlik, derinlik=onerilen_derinlik,
                    icerde=icerde)

    # --- oneri ---
    def oneriler(self, yuzey: dict) -> list[dict]:
        X, Y = yuzey["X"], yuzey["Y"]
        P = yuzey["potansiyel"].copy()
        uygun = yuzey["icerde"].copy()

        for n in self.noktalar:
            d = np.hypot(X - n.x, Y - n.y)
            esik = MAGARA_KACINMA_M if n.tip == "magara" else MIN_MESAFE_MEVCUT_M
            uygun &= d > esik

        aday_P = np.where(uygun, P, -1.0)
        secilen: list[dict] = []
        for _ in range(ONERI_SAYISI):
            idx = np.unravel_index(np.argmax(aday_P), aday_P.shape)
            if aday_P[idx] < 0:
                break
            x, y = X[idx], Y[idx]
            lat, lon = self.xy2ll(x, y)
            derinlik = yuzey["derinlik"][idx]
            secilen.append(dict(
                sira=len(secilen) + 1,
                enlem=lat, boylam=lon,
                potansiyel=float(P[idx]),
                belirsizlik=float(yuzey["belirsizlik"][idx]),
                onerilen_derinlik_m=float(derinlik) if np.isfinite(derinlik) else None,
                en_yakin=self._en_yakin(x, y),
            ))
            aday_P = np.where(np.hypot(X - x, Y - y) < ONERILER_ARASI_MIN_M, -1.0, aday_P)
        return secilen

    def _en_yakin(self, x: float, y: float) -> str:
        n, d = min(((n, math.hypot(n.x - x, n.y - y)) for n in self.noktalar),
                   key=lambda t: t[1])
        return f"{n.isim} ({d:.0f} m)"

    def eksen_acisi(self) -> float:
        """Kanal ekseninin kuzeyden saat yönünde açısı (derece)."""
        ex, ey = self.eksen
        return (math.degrees(math.atan2(ex, ey))) % 180


def renklendir(dizi: np.ndarray, maske: np.ndarray, cmap: str,
               vmin: float, vmax: float) -> np.ndarray:
    """Diziyi RGBA görüntüye çevirir, maske dışını şeffaf yapar."""
    norm = colors.Normalize(vmin=vmin, vmax=vmax, clip=True)
    rgba = matplotlib.colormaps[cmap](norm(dizi))
    rgba[..., 3] = np.where(maske, 0.62, 0.0)
    return (rgba * 255).astype(np.uint8)
