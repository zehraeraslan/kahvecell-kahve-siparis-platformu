# KahveCell

## Docker ile çalıştırma

Docker Desktop'ı yükleyip çalışır durumda bıraktıktan sonra proje klasöründe:

```sh
docker compose up --build
```

- Uygulama: http://localhost:8080
- Backend Swagger: http://localhost:8001/docs
- Arka planda çalıştırma: `docker compose up --build -d`
- Durdurma: `docker compose down`

SQLite veritabanı `kahvecell_data` adlı Docker volume'unda saklanır ve container'lar
kaldırılsa da korunur. Veritabanını ve demo verilerini sıfırlamak için
`docker compose down -v` komutunu çalıştırın; bu komut volume içindeki verileri siler.

İlk çalıştırmada Ankara demo dükkânları ve test hesapları otomatik eklenir.
İmzalama anahtarı yalnızca yerel geliştirme içindir; dağıtım öncesinde
`JWT_SECRET_KEY` ortam değişkenini güvenli, rastgele bir değerle ayarlayın.
