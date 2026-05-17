#!/bin/sh

# Создаем директорию для хранения SSL-сертификатов, если она не существует
mkdir -p /etc/nginx/ssl

CRT="/etc/nginx/ssl/nginx.crt"
KEY="/etc/nginx/ssl/nginx.key"

# Генерируем 2048-битный самоподписанный SSL-сертификат на 10 лет (3650 дней) при его отсутствии
if [ ! -f "$CRT" ] || [ ! -f "$KEY" ]; then
    echo "=== [SSL] Сертификаты не найдены. Генерация самоподписанного сертификата... ==="
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout "$KEY" -out "$CRT" \
        -subj "/C=RU/ST=Moscow/L=Moscow/O=LLM Bot Admin/CN=localhost"
    echo "=== [SSL] Сертификаты успешно сгенерированы! ==="
else
    echo "=== [SSL] Сертификаты уже существуют, генерация не требуется. ==="
fi

# Передаем управление официальному скрипту точки входа Nginx
exec /docker-entrypoint.sh "$@"
