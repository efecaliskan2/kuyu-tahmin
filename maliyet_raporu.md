# Maliyet ve Karar Analizi

> Fiyatlar `data/maliyetler.json` içindeki **yer tutucu** değerlerdir. 
> Gerçek tekliflerinizi girip yeniden çalıştırın: `python maliyet_analizi.py`

## 1. Gözlenen başarı oranları (tarla içi sondajlar)

| Ölçüt | Gözlem | Oran | %95 güven aralığı |
|-------|--------|------|-------------------|
| Verimli kuyu çıkma oranı | 2/8 | 25% | 7% – 59% |
| ≥100 m'ye inen kuyularda suya rastlama | 3/3 | 100% | 44% – 100% |
| <100 m'de bırakılanlarda suya rastlama | 1/4 | 25% | 5% – 70% |

Güven aralıkları geniştir; 8 sondajlık bir geçmişten kesin oran çıkarılamaz. Yine de yön nettir: **yeterince derine inilen her kuyuda suya rastlanmış, sığ bırakılanların çoğunda rastlanmamıştır.** Bu, bazı 'kuru' kuyuların aslında yeterince derin olmadığı anlamına gelebilir.

## 2. Bir verimli kuyu elde etmenin beklenen maliyeti

Hedef derinlik 180 m varsayımıyla:

- Kuru kuyu maliyeti: **295.000 TL**
- Verimli kuyu maliyeti (teçhizat dahil): **355.000 TL**
- Körlemesine sondajla, bir verimli kuyunun beklenen maliyeti: **1.240.000 TL** (başarı oranı 25%)

## 3. Derinleştirme seçeneği (en ucuz test)

Sığ bırakılmış kuru kuyular yeniden kullanılabilir. Yeni kuyu açmak yerine mevcut deliği derinleştirmek, kurulum ve üst kesim maliyetini ortadan kaldırır:

| Kuyu | Mevcut | Hedefe ek | Derinleştirme maliyeti | Yeni kuyuya kıyasla |
|------|--------|-----------|------------------------|---------------------|
| K4 | 60 m | +120 m | 195.000 TL | %34 daha ucuz |
| K5 | 80 m | +100 m | 165.000 TL | %44 daha ucuz |
| K6 | 60 m | +120 m | 195.000 TL | %34 daha ucuz |

Ortalama tasarruf: **%37**. Aynı parayla 1.6 kat daha fazla deneme yapılabilir.

## 4. Jeofizik etüt başabaş noktası

Etüt maliyeti 60.000 TL, kuru kuyu maliyeti 295.000 TL.

Etüt, başarı oranını **20% puandan fazla** artırırsa masrafını çıkarır.
Yani mevcut %25 başarı oranını yaklaşık %45 üzerine taşıyorsa yaptırmaya değer.

Karstik arazide elektrik özdirenç etüdünün çatlak/boşluk zonlarını ayırt etmedeki katkısı genelde bu eşiğin üzerindedir; ancak bunu kendi bölgenizde etüt firmasından referans iş isteyerek doğrulayın.

## 5. Öneri sıralaması

1. **K6 ve K5'i derinleştir** (60 ve 80 m → ~180 m). En ucuz test, en yüksek bilgi getirisi. Tarlanın batı ucu bugüne kadar yeterli derinlikte hiç denenmedi.
2. **Yeni kör sondajdan önce jeofizik etüt yaptır.** Başabaş eşiği düşük.
3. **Yeni kuyu açılacaksa** K1–D2 çevresindeki kuzeydoğu kümesi en çok su gözlenen bölge; ancak K1'in günde 6 saatle sınırlı olması, oradaki haznenin küçük olabileceğini gösterir — yeni kuyu aynı suyu bölebilir.
4. **Güney-orta bölgeden kaçın** (K7 zayıf, M1 mağara, D3 kurumuş).

## 6. Bu analizin sınırı

Bu sayılar mekânsal bir tahmin değildir; geçmiş sonuçların oranı ve maliyet yapısıdır. Nereye vurulacağını jeofizik etüt belirlemelidir. Ayrıntı için `dogrulama_raporu.md`.
