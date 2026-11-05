# SineDesk Relay Sunucusu

Bu sunucu sayesinde SineDesk, AnyDesk gibi **9 haneli ID ile her ağdan** bağlanır
(telefon 4.5G'deyken, bilgisayar evdeyken bile). İçinde lisans anahtarı / gizli bilgi yoktur.

## A) Ücretsiz kurulum — Render.com (önerilen, kolay)
1. Bu `relay_sunucu` klasörünü GitHub'da yeni bir depo olarak yükleyin (örn. `wolkansezer/sinedesk-relay`).
2. https://render.com → GitHub ile giriş → **New → Blueprint** → depoyu seçin → **Apply**.
   (`render.yaml` her şeyi otomatik ayarlar.)
3. Birkaç dakika sonra adres verilir, örn. `https://sinedesk-relay.onrender.com`.
4. Bu adresi:
   - SineDesk → **Ayarlar → Relay sunucusu** kutusuna yazın, **veya**
   - `sinedesk.py` içindeki `DEFAULT_RELAY = ""` satırına yazıp exe'yi yeniden derleyin
     (böylece müşterilerinizde hiçbir ayar gerekmez).
5. Telefondan: tarayıcıda `https://sinedesk-relay.onrender.com` → ID → şifre. Ana Ekrana Ekle ile uygulama gibi kullanın.

Render adresi HTTPS'tir; bağlantı otomatik olarak şifreli (wss) gider.
Not: Ücretsiz planda sunucu uzun süre trafik olmazsa uyuyabilir; bilgisayarlar birkaç saniyede kendiliğinden yeniden bağlanır.
7/24 kesintisiz kullanım için Render'ın ücretli planı veya küçük bir VPS önerilir.

## B) Kendi VPS'iniz (Hetzner, DigitalOcean vb.)
```
pip install aiohttp
python relay_server.py --port 8080
```
veya Docker: `docker build -t sinedesk-relay . && docker run -d -p 8080:8080 --restart always sinedesk-relay`
HTTPS için önüne Caddy koyun: `caddy reverse-proxy --from relay.alanadiniz.com --to :8080`
