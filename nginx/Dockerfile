FROM nginx:alpine

# Устанавливаем openssl для генерации самоподписанных SSL-сертификатов
RUN apk add --no-cache openssl

# Копируем и настраиваем скрипт запуска
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
