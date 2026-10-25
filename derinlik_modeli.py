# -*- coding: utf-8 -*-
"""Sansürlü derinlik modeli: "kaç metreye inersem su bulurum?"

Neden bu model geçerli, mekânsal model değilken
------------------------------------------------
Mekânsal tahmin (nerede su var?) 13 noktayla çözülemedi çünkü heterojenlik
ölçeği kuyu aralığından çok küçük. Ama "ne kadar derine inmeli?" sorusu farklı
bir sorudur ve elimizdeki veri onu taşıyabilir — yeter ki kuru kuyular doğru
yorumlansın.

K5, 80 metrede bırakıldı. Bu "burada su yok" DEĞİL, "ilk 80 metrede su yok"
demektir. İstatistikte buna sağdan sansürlü gözlem denir ve Kaplan-Meier
tahmincisi tam olarak bunun için vardır. Hiçbir parametre aranmadığı için
(dogrulama.py'de çürüttüğümüz) aşırı uyum tuzağı da yoktur.

İki ayrı eğri hesaplanır:
  1. HERHANGİ BİR SU  — damlası bile sayılır
  2. VERİMLİ SU       — sulamaya yeten (verim skoru >= 0.5)

İkincisi asıl karar verilecek olandır: K2 100 m'de suya rastladı ama 5 dakikada
kurudu; bu bir başarı değildir.

Sonra metre başı fiyatla birleştirilip "bir verimli kuyu elde etmenin beklenen
maliyetini en aza indiren durma derinliği" hesaplanır.

Çalıştır: python derinlik_modeli.py
Çıktı:    derinlik_raporu.md, derinlik_egrisi.png
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from tahmin_motoru import DATA

KOK = Path(__file__).parent
RAPOR = KOK / "derinlik_raporu.md"
GRAFIK = KOK / "derinlik_egrisi.png"

VERIMLI_ESIK = 0.5
Z = 1.96

kuyular = json.loads((DATA / "kuyular.json").read_text("utf-8"))["kuyular"]
skorlar = json.loads((DATA / "skorlar.json").read_text("utf-8"))["skorlar"]
F = json.loads((DATA / "maliyetler.json").read_text("utf-8"))


def gozlemler(verimli_mi: bool) -> list[tuple[str, float, bool, str]]:
    """(isim, derinlik, olay_mi, aciklama) listesi. Sadece tarla ici kuyular.

    olay_mi=True  -> aranan su bu derinlikte bulundu
    olay_mi=False -> bu derinliğe kadar bulunamadı (sansürlü)
    """
    cikti = []
    for k in kuyular:
        if k.get("kategori") == "dis":
            continue
        ad = k["isim"]
        s = skorlar.get(ad, {})
        su_d = s.get("su_derinligi_m")
        skor = s.get("verim_skoru", 0)
        toplam = k.get("toplam_derinlik_m") or k.get("magara_girilen_derinlik_m")

        if su_d is not None and (not verimli_mi or skor >= VERIMLI_ESIK):
            cikti.append((ad, float(su_d), True, "su bulundu"))
        else:
            # Aranan suya rastlanmadi: kuyunun indigi derinlige kadar sansurlu
            d = float(su_d) if su_d is not None else float(toplam or 0)
            d = float(toplam or d)
            neden = "kuru" if su_d is None else "su yetersiz"
            cikti.append((ad, d, False, neden))
    return sorted(cikti, key=lambda t: t[1])


def kaplan_meier(gozlem: list[tuple[str, float, bool, str]]):
    """S(d) = derinlik d'ye kadar hâlâ su bulunmamış olma olasılığı.

    Greenwood varyansı ve log-log dönüşümlü %95 güven aralığı ile döner.
    """
    derinlikler = sorted({d for _, d, olay, _ in gozlem if olay})
    n = len(gozlem)
    S, birikim = 1.0, 0.0
    adimlar = [(0.0, 1.0, 1.0, 1.0)]
    for d in derinlikler:
        risk = sum(1 for _, dd, _, _ in gozlem if dd >= d)
        olay = sum(1 for _, dd, o, _ in gozlem if dd == d and o)
        if risk == 0:
            continue
        S *= (1 - olay / risk)
        if risk > olay:
            birikim += olay / (risk * (risk - olay))
        # log-log guven araligi (sinirlarda daha iyi davranir)
        if 0 < S < 1 and birikim > 0:
            se = math.sqrt(birikim) / abs(math.log(S))
            alt = S ** math.exp(Z * se)
            ust = S ** math.exp(-Z * se)
        else:
            alt, ust = (0.0, 1.0) if S <= 0 else (S, S)
        adimlar.append((d, S, max(0.0, alt), min(1.0, ust)))
    return adimlar, n


def olasilik(adimlar, derinlik: float) -> tuple[float, float, float]:
    """Verilen derinliğe kadar su bulma olasılığı (1 - S) ve güven aralığı."""
    S, alt, ust = 1.0, 1.0, 1.0
    for d, s, a, u in adimlar:
        if d <= derinlik:
            S, alt, ust = s, a, u
    return 1 - S, 1 - ust, 1 - alt


def maliyet(derinlik: float, basarili: bool) -> float:
    m = F["kurulum_nakliye_sabit"] + derinlik * F["metre_basi_sondaj"]
    return m + (F["teçhizat_kuyu_basina"] if basarili else 0)


def beklenen_maliyet(p: float, derinlik: float) -> float:
    if p <= 1e-9:
        return float("inf")
    return maliyet(derinlik, True) + (1 - p) / p * maliyet(derinlik, False)


def tl(x: float) -> str:
    if not np.isfinite(x):
        return "—"
    return f"{x:,.0f} {F['para_birimi']}".replace(",", ".")


# --- hesaplar ---
g_her = gozlemler(verimli_mi=False)
g_ver = gozlemler(verimli_mi=True)
km_her, n = kaplan_meier(g_her)
km_ver, _ = kaplan_meier(g_ver)

# Optimal durma derinligi: sadece egrinin basamak noktalari aday olabilir
adaylar = sorted({d for d, *_ in km_ver if d > 0})
tablo = []
for d in adaylar:
    p, pa, pu = olasilik(km_ver, d)
    tablo.append((d, p, pa, pu, beklenen_maliyet(p, d)))
en_iyi = min(tablo, key=lambda t: t[4]) if tablo else None

# 180 m referansi (onceki kaba varsayimimiz)
p180, _, _ = olasilik(km_ver, 180)
e180 = beklenen_maliyet(p180, 180)

# --- duyarlilik: K1 ve K7'nin su derinlikleri tahminiydi ---
duyarlilik = []
for k1_derinlik in (60, 80, 100):
    gecici = [(ad, k1_derinlik if ad == "K1" else d, o, a) for ad, d, o, a in g_ver]
    km_g, _ = kaplan_meier(sorted(gecici, key=lambda t: t[1]))
    ad_g = sorted({d for d, *_ in km_g if d > 0})
    tb = [(d, *olasilik(km_g, d)[:1], beklenen_maliyet(olasilik(km_g, d)[0], d))
          for d in ad_g]
    if tb:
        best = min(tb, key=lambda t: t[2])
        duyarlilik.append((k1_derinlik, best[0], best[1], best[2]))

# --- grafik ---
fig, eksen = plt.subplots(figsize=(9, 5.2))
for km, renk, etiket in [(km_her, "#4c78a8", "Herhangi bir su"),
                         (km_ver, "#d1495b", "Verimli su (sulamaya yeten)")]:
    d = [a[0] for a in km]
    p = [1 - a[1] for a in km]
    pa = [1 - a[3] for a in km]
    pu = [1 - a[2] for a in km]
    d_ = d + [260]
    eksen.step(d_, p + [p[-1]], where="post", color=renk, lw=2.4, label=etiket)
    eksen.fill_between(d_, pa + [pa[-1]], pu + [pu[-1]],
                       step="post", color=renk, alpha=0.13)

# Ayni derinlikteki kuyu etiketleri ust uste binmesin diye kademelendirilir
kullanilan: dict[float, int] = {}
for ad, d, olay, _ in g_ver:
    kat = kullanilan.get(d, 0)
    kullanilan[d] = kat + 1
    eksen.plot(d, -0.045, marker="v" if olay else "|",
               color="#d1495b" if olay else "#888", ms=9,
               clip_on=False, zorder=5)
    eksen.annotate(ad, (d, -0.09 - kat * 0.05), ha="center", fontsize=8,
                   color="#d1495b" if olay else "#666", annotation_clip=False)

if en_iyi:
    eksen.axvline(en_iyi[0], color="#2a9d8f", ls="--", lw=1.6)
    eksen.annotate(f"maliyet-optimal durma\nderinliği: {en_iyi[0]:.0f} m",
                   (en_iyi[0] + 6, 0.06), color="#2a9d8f", fontsize=9)

eksen.set_xlabel("Sondaj derinliği (m)", labelpad=34)
eksen.set_ylabel("Suya rastlama olasılığı")
eksen.set_title("Derinliğe göre su bulma olasılığı — Kaplan-Meier (gölge: %95 güven aralığı)")
eksen.set_xlim(0, 260)
eksen.set_ylim(0, 1.02)
eksen.grid(alpha=0.25)
eksen.legend(loc="upper left", frameon=False)
fig.tight_layout()
fig.savefig(GRAFIK, dpi=150)

# --- rapor ---
sat = [
    "# Derinlik Modeli — \"Kaç metreye inmeli?\"",
    "",
    f"Tarla içi {n} sondaj noktası kullanıldı (D1–D5 dış kuyulardır ve su "
    "derinlikleri bilinmediği için bu analize giremez).",
    "",
    "## Gözlem tablosu (verimli su için)",
    "",
    "| Kuyu | Derinlik | Durum |",
    "|------|----------|-------|",
]
for ad, d, olay, aciklama in g_ver:
    sat.append(f"| {ad} | {d:.0f} m | {'✅ verimli su bulundu' if olay else f'⊣ sansürlü ({aciklama})'} |")

sat += [
    "",
    "Sansürlü demek: o derinliğe kadar aranan su bulunamadı, ama daha derinde "
    "olup olmadığı **bilinmiyor**. Bu kuyular 'başarısızlık' olarak sayılmaz — "
    "sayılsaydı model, hiç test edilmemiş derinlikleri haksız yere cezalandırırdı.",
    "",
    "## Sonuç: derinliğe göre su bulma olasılığı",
    "",
    "| Derinlik | Herhangi bir su | Verimli su | Verimli su %95 GA |",
    "|----------|-----------------|------------|-------------------|",
]
for d in (30, 60, 80, 100, 150, 220):
    ph, _, _ = olasilik(km_her, d)
    pv, pa, pu = olasilik(km_ver, d)
    sat.append(f"| {d} m | {ph:.0%} | {pv:.0%} | {pa:.0%} – {pu:.0%} |")

sat += [
    "",
    "## Maliyet-optimal durma derinliği",
    "",
    "| Aday derinlik | Verimli su olasılığı | 1 verimli kuyunun beklenen maliyeti |",
    "|---------------|----------------------|--------------------------------------|",
]
for d, p, pa, pu, e in tablo:
    isaret = " ⬅ **en ucuz**" if en_iyi and d == en_iyi[0] else ""
    sat.append(f"| {d:.0f} m | {p:.0%} | {tl(e)}{isaret} |")
sat.append(f"| 180 m (önceki kaba varsayımımız) | {p180:.0%} | {tl(e180)} |")

if en_iyi:
    fark = e180 - en_iyi[4]
    sat += [
        "",
        f"**{en_iyi[0]:.0f} metrede durmak**, 180 metreye inmekten "
        f"**{tl(fark)}** daha ucuz (verimli kuyu başına).",
        "",
        "Sebebi tek cümlede: 100 metreden derinde bugüne kadar **hiç verimli su "
        "bulunmadı**. K7 220 metreye indi ve 8 saatte 40 dakika veren zayıf bir "
        "kuyu çıktı. Yani derine inmek suya rastlama şansını artırıyor ama "
        "**işe yarar** su bulma şansını artırmıyor.",
    ]

sat += [
    "",
    "## Duyarlılık kontrolü",
    "",
    "K1'in su derinliği kesin bilinmiyor (kuyu 100 m, su hangi metrede geldi "
    "kayıtlı değil). Farklı varsayımlarla optimal derinlik:",
    "",
    "| K1 su derinliği varsayımı | Optimal durma | Olasılık | Beklenen maliyet |",
    "|---------------------------|---------------|----------|------------------|",
]
for varsayim, opt, p, e in duyarlilik:
    sat.append(f"| {varsayim} m | {opt:.0f} m | {p:.0%} | {tl(e)} |")

sat += [
    "",
    "Sonuç varsayıma duyarlı — bu yüzden **K1'in gerçek su derinliğini "
    "sondajcıdan veya kuyu kaydından öğrenmek**, bu modeli tek hamlede "
    "güçlendirecek en değerli bilgidir.",
    "",
    "## Bu modelin dürüst sınırları",
    "",
    "1. **Güven aralıkları çok geniş.** 2 verimli su olayı var. Nokta tahmini "
    "yön gösterir, kesinlik iddia etmez.",
    "2. **Sansürleme muhtemelen bağımsız değil.** Sondajcı büyük ihtimalle "
    "'burada iş yok' göründüğü için erken bıraktı. Kaplan-Meier, bırakma "
    "kararının rastgele olduğunu varsayar; bu varsayım burada tam sağlanmıyor "
    "ve sonucu **iyimser** yönde saptırır.",
    "3. **K1 ve K7'nin su derinlikleri tahmindir**, kuyu toplam derinliğinden "
    "türetildi.",
    "4. Bu model **nerede** sorusunu cevaplamaz, sadece **ne kadar derine** "
    "sorusunu cevaplar. Nerede sorusu için `dogrulama_raporu.md`.",
    "",
    "## Karar için anlamı",
    "",
    f"- Yeni kuyuda hedef derinlik ~{en_iyi[0]:.0f} m olmalı, 180-220 m değil." if en_iyi else "",
    "- K5 (80 m) ve K6 (60 m) derinleştirilecekse hedef aynı olmalı; ikisi de "
    "verimli suyun görüldüğü 100 m eşiğinin altında kaldı.",
    "- K7'yi (220 m, zayıf) daha da derinleştirmek veriye göre desteklenmiyor.",
]

RAPOR.write_text("\n".join(s for s in sat if s) + "\n", "utf-8")

# --- konsol ---
print("VERIMLI SU icin gozlemler:")
for ad, d, olay, aciklama in g_ver:
    print(f"  {ad:3} {d:6.0f} m  {'OLAY (verimli su)' if olay else f'sansurlu ({aciklama})'}")
print("\nDerinlige gore VERIMLI su bulma olasiligi:")
for d in (30, 60, 80, 100, 150, 220):
    p, pa, pu = olasilik(km_ver, d)
    print(f"  {d:3d} m : {p:5.1%}   (%95 GA {pa:.0%}-{pu:.0%})")
print("\nMaliyet-optimal durma derinligi:")
for d, p, pa, pu, e in tablo:
    print(f"  {d:5.0f} m  p={p:5.1%}  beklenen maliyet={tl(e)}"
          + ("   <-- EN UCUZ" if en_iyi and d == en_iyi[0] else ""))
print(f"  {180:5.0f} m  p={p180:5.1%}  beklenen maliyet={tl(e180)}  (onceki varsayim)")
print(f"\nRapor: {RAPOR}\nGrafik: {GRAFIK}")
