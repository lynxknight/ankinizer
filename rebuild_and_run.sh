docker build -t ankinizer -f build/Dockerfile .
docker rm -f ankinizer_container || true
docker run -d --name ankinizer_container \
    -e ANKI_USERNAME=$(cat .sensitive/.username) \
    -e ANKI_PASSWORD=$(cat .sensitive/.password) \
    -e TELEGRAM_BOT_TOKEN=$(cat .sensitive/.telegram_bot_token) \
    ankinizer
echo "Docker run status: $?"

if [ "$LOGS" = "1" ]; then
    docker logs -f ankinizer_container
fi
