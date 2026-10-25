# -*- coding: utf-8 -*-
"""Karar ve maliyet analizi: hangi strateji kuyu başına maliyeti düşürür?

Mekânsal tahmin modeli bu veriyle geçerli çıkmadığı için (bkz. dogrulama.py),
karar verirken kullanılabilecek şey mekânsal tahmin değil, doğrudan gözlenen
BAŞARI ORANLARI ve maliyet yapısıdır.

Tüm oranlar Wilson skor aralığıyla birlikte verilir; 8 kuyuluk bir örneklemde
tek bir yüzde vermek yanıltıcı olur, gerçek belirsizlik aralık olarak görünmelidir.

Fiyatlar `data/maliyetler.json` içinde — kendi rakamlarınızla değiştirin.

Çalıştır: python maliyet_analizi.py
Çıktı:    maliyet_raporu.md
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from tahmin_motoru import DATA

KOK = Path(__file__).parent
RAPOR = KOK / "maliyet_raporu.md"

F = json.loads((DATA / "maliyetler.json").read_text("utf-8"))
kuyular = json.loads((DATA / "kuyular.json").read_text("utf-8"))["kuyular"]
skorlar = json.loads((DATA / "skorlar.json").read_text("utf-8"))["skorlar"]


def wilson(basari: int, toplam: int, z: float = 1.96) -> tuple[float, float, float]:
    """Oran + %95 Wilson güven aralığı. Küçük örneklemde doğru yöntem budur."""
    if toplam == 0:
        return (float("nan"),) * 3
    p = basari / toplam
    payda = 1 + z * z / toplam
    merkez = (p + z * z / (2 * toplam)) / payda
    yari = z * math.sqrt(p * (1 - p) / toplam + z * z / (4 * toplam * toplam)) / payda
    return p, max(0.0, merkez - yari), min(1.0, merkez + yari)


def tl(x: float) -> str:
    return f"{x:,.0f} {F['para_birimi']}".replace(",", ".")


# --- gozlenen oranlar (sadece tarla ici sondajlar) ---
ic = [k for k in kuyular if k.get("kategori") != "dis"]
verimli = [k for k in ic if skorlar.get(k["isim"], {}).get("verim_skoru", 0) >= 0.5]
derin = [k for k in ic if (k.get("toplam_derinlik_m") or 0) >= 100]
derin_su = [k for k in derin
            if skorlar.get(k["isim"], {}).get("su_derinligi_m") is not None]
sig = [k for k in ic if 0 < (k.get("toplam_derinlik_m") or 0) < 100]
sig_su = [k for k in sig
          if skorlar.get(k["isim"], {}).get("su_derinligi_m") is not None]

p_verimli, alt_v, ust_v = wilson(len(verimli), len(ic))
p_derin, alt_d, ust_d = wilson(len(derin_su), len(derin))
p_sig, alt_s, ust_s = wilson(len(sig_su), len(sig))

# --- maliyet senaryolari ---
HEDEF_DERINLIK = 180


def yeni_kuyu_maliyeti(derinlik: int, basarili: bool) -> float:
    m = F["kurulum_nakliye_sabit"] + derinlik * F["metre_basi_sondaj"]
    return m + (F["teçhizat_kuyu_basina"] if basarili else 0)


def beklenen_maliyet(p: float, derinlik: int) -> float:
    """Bir ADET verimli kuyu elde etmenin beklenen toplam maliyeti."""
    if p <= 0:
        return float("inf")
    kuru = yeni_kuyu_maliyeti(derinlik, False)
    sulu = yeni_kuyu_maliyeti(derinlik, True)
    return sulu + (1 - p) / p * kuru


kor_maliyet = beklenen_maliyet(p_verimli, HEDEF_DERINLIK)

# Derinlestirme adaylari
adaylar = [k for k in ic
           if k["tip"] == "kuru" and 0 < (k.get("toplam_derinlik_m") or 0) < 100]
derinlestirme = []
for k in adaylar:
    ek = HEDEF_DERINLIK - k["toplam_derinlik_m"]
    mal = F["derinlestirme_ek_kurulum"] + ek * F["metre_basi_sondaj"]
    derinlestirme.append((k["isim"], k["toplam_derinlik_m"], ek, mal))

yeni_kuru = yeni_kuyu_maliyeti(HEDEF_DERINLIK, False)
ort_derinlestirme = sum(d[3] for d in derinlestirme) / len(derinlestirme) if derinlestirme else 0
tasarruf_orani = 1 - ort_derinlestirme / yeni_kuru if yeni_kuru else 0

# Jeofizik basabas noktasi
basabas_artis = F["jeofizik_etut"] / yeni_kuru

satir = [
    "# Maliyet ve Karar Analizi",
    "",
    "> Fiyatlar `data/maliyetler.json` içindeki **yer tutucu** değerlerdir. ",
    "> Gerçek tekliflerinizi girip yeniden çalıştırın: `python maliyet_analizi.py`",
    "",
    "## 1. Gözlenen başarı oranları (tarla içi sondajlar)",
    "",
    "| Ölçüt | Gözlem | Oran | %95 güven aralığı |",
    "|-------|--------|------|-------------------|",
    f"| Verimli kuyu çıkma oranı | {len(verimli)}/{len(ic)} | {p_verimli:.0%} | "
    f"{alt_v:.0%} – {ust_v:.0%} |",
    f"| ≥100 m'ye inen kuyularda suya rastlama | {len(derin_su)}/{len(derin)} | "
    f"{p_derin:.0%} | {alt_d:.0%} – {ust_d:.0%} |",
    f"| <100 m'de bırakılanlarda suya rastlama | {len(sig_su)}/{len(sig)} | "
    f"{p_sig:.0%} | {alt_s:.0%} – {ust_s:.0%} |",
    "",
    "Güven aralıkları geniştir; 8 sondajlık bir geçmişten kesin oran çıkarılamaz. "
    "Yine de yön nettir: **yeterince derine inilen her kuyuda suya rastlanmış, "
    "sığ bırakılanların çoğunda rastlanmamıştır.** Bu, bazı 'kuru' kuyuların "
    "aslında yeterince derin olmadığı anlamına gelebilir.",
    "",
    "## 2. Bir verimli kuyu elde etmenin beklenen maliyeti",
    "",
    f"Hedef derinlik {HEDEF_DERINLIK} m varsayımıyla:",
    "",
    f"- Kuru kuyu maliyeti: **{tl(yeni_kuru)}**",
    f"- Verimli kuyu maliyeti (teçhizat dahil): **{tl(yeni_kuyu_maliyeti(HEDEF_DERINLIK, True))}**",
    f"- Körlemesine sondajla, bir verimli kuyunun beklenen maliyeti: "
    f"**{tl(kor_maliyet)}** (başarı oranı {p_verimli:.0%})",
    "",
    "## 3. Derinleştirme seçeneği (en ucuz test)",
    "",
    "Sığ bırakılmış kuru kuyular yeniden kullanılabilir. Yeni kuyu açmak yerine "
    "mevcut deliği derinleştirmek, kurulum ve üst kesim maliyetini ortadan kaldırır:",
    "",
    "| Kuyu | Mevcut | Hedefe ek | Derinleştirme maliyeti | Yeni kuyuya kıyasla |",
    "|------|--------|-----------|------------------------|---------------------|",
]
for ad, mevcut, ek, mal in derinlestirme:
    satir.append(f"| {ad} | {mevcut} m | +{ek} m | {tl(mal)} | "
                 f"%{100*(1-mal/yeni_kuru):.0f} daha ucuz |")

satir += [
    "",
    f"Ortalama tasarruf: **%{100*tasarruf_orani:.0f}**. Aynı parayla "
    f"{yeni_kuru/ort_derinlestirme:.1f} kat daha fazla deneme yapılabilir." if ort_derinlestirme else "",
    "",
    "## 4. Jeofizik etüt başabaş noktası",
    "",
    f"Etüt maliyeti {tl(F['jeofizik_etut'])}, kuru kuyu maliyeti {tl(yeni_kuru)}.",
    "",
    f"Etüt, başarı oranını **{basabas_artis:.0%} puandan fazla** artırırsa masrafını çıkarır.",
    f"Yani mevcut %{100*p_verimli:.0f} başarı oranını yaklaşık "
    f"%{100*(p_verimli+basabas_artis):.0f} üzerine taşıyorsa yaptırmaya değer.",
    "",
    "Karstik arazide elektrik özdirenç etüdünün çatlak/boşluk zonlarını ayırt "
    "etmedeki katkısı genelde bu eşiğin üzerindedir; ancak bunu kendi bölgenizde "
    "etüt firmasından referans iş isteyerek doğrulayın.",
    "",
    "## 5. Öneri sıralaması",
    "",
    "1. **K6 ve K5'i derinleştir** (60 ve 80 m → ~180 m). En ucuz test, en yüksek "
    "bilgi getirisi. Tarlanın batı ucu bugüne kadar yeterli derinlikte hiç "
    "denenmedi.",
    "2. **Yeni kör sondajdan önce jeofizik etüt yaptır.** Başabaş eşiği düşük.",
    "3. **Yeni kuyu açılacaksa** K1–D2 çevresindeki kuzeydoğu kümesi en çok su "
    "gözlenen bölge; ancak K1'in günde 6 saatle sınırlı olması, oradaki haznenin "
    "küçük olabileceğini gösterir — yeni kuyu aynı suyu bölebilir.",
    "4. **Güney-orta bölgeden kaçın** (K7 zayıf, M1 mağara, D3 kurumuş).",
    "",
    "## 6. Bu analizin sınırı",
    "",
    "Bu sayılar mekânsal bir tahmin değildir; geçmiş sonuçların oranı ve maliyet "
    "yapısıdır. Nereye vurulacağını jeofizik etüt belirlemelidir. "
    "Ayrıntı için `dogrulama_raporu.md`.",
]

RAPOR.write_text("\n".join(s for s in satir if s is not None) + "\n", "utf-8")

print(f"Verimli kuyu orani     : {len(verimli)}/{len(ic)} = {p_verimli:.0%} "
      f"(%95 GA: {alt_v:.0%}-{ust_v:.0%})")
print(f">=100 m'de suya rastlama: {len(derin_su)}/{len(derin)} = {p_derin:.0%}")
print(f"<100 m'de suya rastlama : {len(sig_su)}/{len(sig)} = {p_sig:.0%}")
print(f"\nKor sondajla 1 verimli kuyunun beklenen maliyeti: {tl(kor_maliyet)}")
print(f"Derinlestirme ortalama maliyeti: {tl(ort_derinlestirme)} "
      f"(yeni kuyudan %{100*tasarruf_orani:.0f} ucuz)")
print(f"Jeofizik basabas: basari oranini {basabas_artis:.0%} puan artirmali")
print(f"\nRapor: {RAPOR}")
