# Derinlik Modeli — "Kaç metreye inmeli?"
Tarla içi 8 sondaj noktası kullanıldı (D1–D5 dış kuyulardır ve su derinlikleri bilinmediği için bu analize giremez).
## Gözlem tablosu (verimli su için)
| Kuyu | Derinlik | Durum |
|------|----------|-------|
| M1 | 20 m | ⊣ sansürlü (kuru) |
| K3 | 30 m | ✅ verimli su bulundu |
| K4 | 60 m | ⊣ sansürlü (kuru) |
| K6 | 60 m | ⊣ sansürlü (kuru) |
| K5 | 80 m | ⊣ sansürlü (kuru) |
| K1 | 90 m | ✅ verimli su bulundu |
| K2 | 100 m | ⊣ sansürlü (su yetersiz) |
| K7 | 220 m | ⊣ sansürlü (su yetersiz) |
Sansürlü demek: o derinliğe kadar aranan su bulunamadı, ama daha derinde olup olmadığı **bilinmiyor**. Bu kuyular 'başarısızlık' olarak sayılmaz — sayılsaydı model, hiç test edilmemiş derinlikleri haksız yere cezalandırırdı.
## Sonuç: derinliğe göre su bulma olasılığı
| Derinlik | Herhangi bir su | Verimli su | Verimli su %95 GA |
|----------|-----------------|------------|-------------------|
| 30 m | 14% | 14% | 2% – 67% |
| 60 m | 14% | 14% | 2% – 67% |
| 80 m | 14% | 14% | 2% – 67% |
| 100 m | 71% | 43% | 11% – 92% |
| 150 m | 71% | 43% | 11% – 92% |
| 220 m | 100% | 43% | 11% – 92% |
## Maliyet-optimal durma derinliği
| Aday derinlik | Verimli su olasılığı | 1 verimli kuyunun beklenen maliyeti |
|---------------|----------------------|--------------------------------------|
| 30 m | 14% | 550.000 TL |
| 90 m | 43% | 433.333 TL ⬅ **en ucuz** |
| 180 m (önceki kaba varsayımımız) | 43% | 748.333 TL |
**90 metrede durmak**, 180 metreye inmekten **315.000 TL** daha ucuz (verimli kuyu başına).
Sebebi tek cümlede: 100 metreden derinde bugüne kadar **hiç verimli su bulunmadı**. K7 220 metreye indi ve 8 saatte 40 dakika veren zayıf bir kuyu çıktı. Yani derine inmek suya rastlama şansını artırıyor ama **işe yarar** su bulma şansını artırmıyor.
## Duyarlılık kontrolü
K1'in su derinliği kesin bilinmiyor (kuyu 100 m, su hangi metrede geldi kayıtlı değil). Farklı varsayımlarla optimal derinlik:
| K1 su derinliği varsayımı | Optimal durma | Olasılık | Beklenen maliyet |
|---------------------------|---------------|----------|------------------|
| 60 m | 60 m | 29% | 462.500 TL |
| 80 m | 80 m | 36% | 466.000 TL |
| 100 m | 100 m | 43% | 468.333 TL |
Sonuç varsayıma duyarlı — bu yüzden **K1'in gerçek su derinliğini sondajcıdan veya kuyu kaydından öğrenmek**, bu modeli tek hamlede güçlendirecek en değerli bilgidir.
## Bu modelin dürüst sınırları
1. **Güven aralıkları çok geniş.** 2 verimli su olayı var. Nokta tahmini yön gösterir, kesinlik iddia etmez.
2. **Sansürleme muhtemelen bağımsız değil.** Sondajcı büyük ihtimalle 'burada iş yok' göründüğü için erken bıraktı. Kaplan-Meier, bırakma kararının rastgele olduğunu varsayar; bu varsayım burada tam sağlanmıyor ve sonucu **iyimser** yönde saptırır.
3. **K1 ve K7'nin su derinlikleri tahmindir**, kuyu toplam derinliğinden türetildi.
4. Bu model **nerede** sorusunu cevaplamaz, sadece **ne kadar derine** sorusunu cevaplar. Nerede sorusu için `dogrulama_raporu.md`.
## Karar için anlamı
- Yeni kuyuda hedef derinlik ~90 m olmalı, 180-220 m değil.
- K5 (80 m) ve K6 (60 m) derinleştirilecekse hedef aynı olmalı; ikisi de verimli suyun görüldüğü 100 m eşiğinin altında kaldı.
- K7'yi (220 m, zayıf) daha da derinleştirmek veriye göre desteklenmiyor.
