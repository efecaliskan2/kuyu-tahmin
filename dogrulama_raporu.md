# Model Doğrulama Raporu

Veri noktası: **13** (5 verimli, 8 zayıf/kuru)
Denenen parametre kombinasyonu: **2592**
Permütasyon denemesi: **500**

## Sonuçlar

| Ölçüt | Değer |
|-------|-------|
| Gerçek veride en iyi LOO becerisi | 0.327 |
| En iyi yönsüz (izotropik) model | nan |
| Karıştırılmış veride ortalama beceri | 0.325 |
| Karıştırılmış veride %95 dilim | 0.537 |
| **p-değeri** | **0.452** |

## Karar

**Bulunan mekânsal yapı istatistiksel olarak anlamlı değildir.** Rastgele karıştırılmış skorlarla yapılan aynı arama, gerçek veriyle aynı düzeyde beceri üretiyor. Bu, becerinin veriden değil, çok sayıda parametre kombinasyonu denenmesinden geldiğini gösterir.

Bu nedenle düzgün geçişli bir 'su potansiyeli' ısı haritası üretilmemektedir: bilimsel görünen ama tahmin gücü rastgeleden farksız bir harita, sondaj kararlarını yanlış yönlendirir.

Bunun yerine `kanit_haritasi.py` doğrudan gözleme dayalı kanıt haritasını, `maliyet_analizi.py` ise karar/maliyet analizini üretir.

## Nedeni

Tarlada 47-49 m arayla sulu/kuru kuyu çiftleri var (K3-K4, K1-K2). Yani yeraltı yapısı, kuyular arası tipik mesafeden (~300 m) çok daha küçük ölçekte değişiyor. Karstik arazide beklenen budur: su dar kanallarda akar. Bu ölçekteki değişimi yakalamak için mevcut 13 nokta matematiksel olarak yetersizdir.

## Bunu değiştirecek veriler

- Jeofizik etüt (elektrik özdirenç / ERT-VES): kanalları doğrudan görüntüler
- Her yeni kuyuda tabaka kayıtları (hangi derinlikte hangi formasyon)
- Kuru kuyularda statik su seviyesi ölçümleri
- Ek koku/boya testleri (özellikle kokunun gelmediği kuyular)
