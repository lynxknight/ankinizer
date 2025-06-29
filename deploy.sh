docker build -t ankinizer -f build/Dockerfile . && \
docker tag ankinizer lynxknight/ankinizer:latest && \
docker push lynxknight/ankinizer:latest && \
ssh 192.168.1.173 "/home/zhuk/pull_and_run_ankinizer.sh"