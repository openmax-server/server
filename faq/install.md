# Установка

## Вручную

1. Склонируйте репозиторий
2. Установите зависимости
```bash
pip install -r requirements.txt
```

3. Сгенерируйте сертификат

Для тестирования (самоподписанный):
```bash
openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365
```

Для прода — [Let's Encrypt](https://certbot.eff.org/):
```bash
apt install certbot
certbot certonly --standalone -d openmax.su
```

4. Настройте сервер (пример в `.env.example`)
5. Импортируйте схему таблиц в свою базу данных из `tables.sql`
6. Запустите сервер
```bash
python3 main.py
```

7. Создайте пользователя через Telegram бот (`/register`)
8. Зайдите со своего любимого клиента

---

## Docker

1. Склонируйте репозиторий
2. Настройте `.env` (пример в `.env.example`), укажите `db_user` отличный от `root`
3. Получите сертификат Let's Encrypt:
```bash
apt install certbot
certbot certonly --standalone -d openmax.su
```

Укажите домен и пути в `.env`:
```
certfile=/certs/cert.pem
keyfile=/certs/key.pem
domain=openmax.su
```

4. Запустите
```bash
docker compose up -d
```

База данных инициализируется автоматически из `tables.sql`.

5. Создайте пользователя через Telegram бот (`/register`)
6. Зайдите со своего любимого клиента

---

## SMS-шлюз

По умолчанию коды авторизации доставляются через Telegram бот. Если вы хотите принимать пользователей с произвольными номерами без привязки к Telegram — поднимите [SMS Gateway](https://github.com/openmax-server/server/sms-gateway), укажите его адрес в `.env` и отключите Telegram бот:
```
telegram_bot_enabled=false
sms_gateway_url=http://localhost:8100/sms-gateway
```

Клиент MAX ожидает 6-значный код. Если ваш SMS-провайдер отправляет 5-значные коды и не поддерживает настройку длины — сервер автоматически дублирует последнюю цифру: `26541` → `265411`. Пользователь получает SMS с 5 цифрами и вводит их дважды последнюю: `2-6-5-4-1-1`.

---

## Автопродление сертификата
```bash
certbot renew --deploy-hook "docker compose -f /opt/server/docker-compose.yml restart app"
```