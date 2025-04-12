docker build -t ankinizer -f build/Dockerfile .
docker tag ankinizer lynxknight/ankinizer:latest
docker push lynxknight/ankinizer:latest