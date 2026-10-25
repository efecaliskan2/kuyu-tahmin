# -*- coding: utf-8 -*-
"""Mekânsal tahmin modelinin gerçekten işe yarayıp yaramadığını sınar.

İki aşama
---------
1) KALİBRASYON (leave-one-out): her kuyu sırayla dışarıda bırakılır, kalanlardan
   tahmin edilir. Beceri = 1 - HataModel / HataReferans. Referans, hiçbir mekânsal
   bilgi kullanmayan "herkese ortalamayı ver" modelidir.

2) PERMÜTASYON TESTİ: asıl soru şudur — bulunan beceri gerçek bir yapıdan mı
   geliyor, yoksa yüzlerce parametre kombinasyonu denenirken rastlantısal olarak
   mı yakalandı? Skorlar konumlar arasında rastgele karıştırılıp aynı arama
   tekrarlanır. Gerçek verinin becerisi, karıştırılmış verilerin dağılımından
   belirgin şekilde yüksek değilse model kullanılamaz.

Bu dosya kasıtlı olarak modeli çürütmeye çalışır. Sonuç olumsuzsa harita
üretilmez; çünkü bilimsel görünen ama rastgeleden farksız bir harita, kuyu
kararlarını yanlış yönlendirir ve doğrudan para kaybettirir.

Çalıştır: python dogrulama.py
Çıktı:    data/model_parametreleri.json, dogrulama_raporu.md
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from tahmin_motoru import DATA, Model

KOK = Path(__file__).parent
PARAM = DATA / "model_parametreleri.json"
RAPOR = KOK / "dogrulama_raporu.md"

ACI_IZGARA = np.arange(0, 180, 5)
EKSEN_IZGARA = [90, 130, 200, 300]
DIK_IZGARA = [10, 12, 15, 20, 25, 35]
PSEUDO_IZGARA = [0.15, 0.3, 0.7]
PERMUTASYON = 500
TOHUM = 20260809


def agirlik_yigini(X, Y, G):
    """Tüm parametre kombinasyonları için (k, n, n) ağırlık matrisleri."""
    DX = X[None, :] - X[:, None]
    DY = Y[None, :] - Y[:, None]
    W_listesi, params = [], []
    for aci in ACI_IZGARA:
        a = math.radians(float(aci))
        ex, ey = math.sin(a), math.cos(a)
        d_e = DX * ex + DY * ey
        d_d = -DX * ey + DY * ex
        for me in EKSEN_IZGARA:
            for md in DIK_IZGARA:
                W = np.exp(-0.5 * ((d_e / me) ** 2 + (d_d / md) ** 2)) * G[None, :]
                np.fill_diagonal(W, 0.0)
                for ps in PSEUDO_IZGARA:
                    W_listesi.append(W)
                    params.append((int(aci), me, md, ps))
    return np.array(W_listesi), np.array([p[3] for p in params])[:, None], params


def beceriler(W_yigin, ps_dizi, skorlar):
    """Her parametre kombinasyonu için LOO becerisi."""
    prior = skorlar.mean()
    tahmin = (W_yigin @ skorlar + ps_dizi * prior) / (W_yigin.sum(axis=2) + ps_dizi)
    hata = np.abs(tahmin - skorlar[None, :]).mean(axis=1)
    ref = (skorlar.sum() - skorlar) / (len(skorlar) - 1)
    return 1 - hata / np.abs(ref - skorlar).mean()


def main() -> None:
    model = Model()
    N = model.noktalar
    X = np.array([p.x for p in N])
    Y = np.array([p.y for p in N])
    G = np.array([p.guven for p in N])
    S = np.array([p.skor for p in N])

    W_yigin, ps_dizi, params = agirlik_yigini(X, Y, G)
    b = beceriler(W_yigin, ps_dizi, S)
    en_iyi_i = int(np.argmax(b))
    gercek_beceri = float(b[en_iyi_i])
    aci, me, md, ps = params[en_iyi_i]

    # Izotropik referans
    izo_maske = np.array([p[1] == p[2] for p in params])
    izo_beceri = float(b[izo_maske].max()) if izo_maske.any() else float("nan")

    # Permutasyon testi
    rng = np.random.default_rng(TOHUM)
    null = np.array([float(beceriler(W_yigin, ps_dizi, rng.permutation(S)).max())
                     for _ in range(PERMUTASYON)])
    p_deger = float((null >= gercek_beceri).mean())
    anlamli = p_deger < 0.05

    print(f"Parametre kombinasyonu: {len(params)}, permutasyon: {PERMUTASYON}")
    print(f"\nGercek veri en iyi LOO becerisi : {gercek_beceri:.3f}")
    print(f"  (aci={aci}, eksen={me} m, dik={md} m, pseudo={ps})")
    print(f"Karistirilmis veri becerisi     : ortalama {null.mean():.3f}, "
          f"%95 dilim {np.quantile(null, 0.95):.3f}, max {null.max():.3f}")
    print(f"\np-degeri = {p_deger:.3f}")
    print("KARAR: " + ("Yapi anlamli, mekansal model kullanilabilir."
                       if anlamli else
                       "Yapi ANLAMLI DEGIL. Mekansal tahmin haritasi uretilmemeli."))

    PARAM.write_text(json.dumps({
        "aciklama": "dogrulama.py tarafindan uretildi",
        "en_iyi_parametreler": {
            "eksen_acisi_derece": aci, "menzil_eksen_m": me,
            "menzil_dik_m": md, "pseudo_agirlik": ps,
        },
        "loo_beceri": round(gercek_beceri, 4),
        "izotropik_beceri": round(izo_beceri, 4),
        "permutasyon_ortalama": round(float(null.mean()), 4),
        "permutasyon_p_degeri": round(p_deger, 4),
        "istatistiksel_olarak_anlamli": bool(anlamli),
        "karar": ("mekansal model kullanilabilir" if anlamli
                  else "mekansal tahmin haritasi uretilmemeli - veri yetersiz"),
    }, ensure_ascii=False, indent=2), "utf-8")

    RAPOR.write_text("\n".join([
        "# Model Doğrulama Raporu",
        "",
        f"Veri noktası: **{len(N)}** ({sum(1 for n in N if n.skor >= 0.5)} verimli, "
        f"{sum(1 for n in N if n.skor < 0.5)} zayıf/kuru)",
        f"Denenen parametre kombinasyonu: **{len(params)}**",
        f"Permütasyon denemesi: **{PERMUTASYON}**",
        "",
        "## Sonuçlar",
        "",
        "| Ölçüt | Değer |",
        "|-------|-------|",
        f"| Gerçek veride en iyi LOO becerisi | {gercek_beceri:.3f} |",
        f"| En iyi yönsüz (izotropik) model | {izo_beceri:.3f} |",
        f"| Karıştırılmış veride ortalama beceri | {null.mean():.3f} |",
        f"| Karıştırılmış veride %95 dilim | {np.quantile(null, 0.95):.3f} |",
        f"| **p-değeri** | **{p_deger:.3f}** |",
        "",
        "## Karar",
        "",
        ("Yapı istatistiksel olarak anlamlı; mekânsal tahmin haritası üretilebilir."
         if anlamli else
         "**Bulunan mekânsal yapı istatistiksel olarak anlamlı değildir.** "
         "Rastgele karıştırılmış skorlarla yapılan aynı arama, gerçek veriyle "
         "aynı düzeyde beceri üretiyor. Bu, becerinin veriden değil, çok sayıda "
         "parametre kombinasyonu denenmesinden geldiğini gösterir.\n\n"
         "Bu nedenle düzgün geçişli bir 'su potansiyeli' ısı haritası "
         "üretilmemektedir: bilimsel görünen ama tahmin gücü rastgeleden farksız "
         "bir harita, sondaj kararlarını yanlış yönlendirir.\n\n"
         "Bunun yerine `kanit_haritasi.py` doğrudan gözleme dayalı kanıt "
         "haritasını, `maliyet_analizi.py` ise karar/maliyet analizini üretir."),
        "",
        "## Nedeni",
        "",
        "Tarlada 47-49 m arayla sulu/kuru kuyu çiftleri var (K3-K4, K1-K2). "
        "Yani yeraltı yapısı, kuyular arası tipik mesafeden (~300 m) çok daha "
        "küçük ölçekte değişiyor. Karstik arazide beklenen budur: su dar "
        "kanallarda akar. Bu ölçekteki değişimi yakalamak için mevcut 13 nokta "
        "matematiksel olarak yetersizdir.",
        "",
        "## Bunu değiştirecek veriler",
        "",
        "- Jeofizik etüt (elektrik özdirenç / ERT-VES): kanalları doğrudan görüntüler",
        "- Her yeni kuyuda tabaka kayıtları (hangi derinlikte hangi formasyon)",
        "- Kuru kuyularda statik su seviyesi ölçümleri",
        "- Ek koku/boya testleri (özellikle kokunun gelmediği kuyular)",
    ]) + "\n", "utf-8")

    print(f"\nYazildi: {PARAM}\n         {RAPOR}")


if __name__ == "__main__":
    main()
