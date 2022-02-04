# /usr/bin/bash
# ref https://aws.amazon.com/premiumsupport/knowledge-center/lambda-layer-simulated-docker/
docker run -v "$PWD":/var/task "lambci/lambda:build-python3.8" /bin/sh -c "pip install twython==3.9.1 psycopg2-binary==2.9.1 -t python/lib/python3.8/site-packages/; exit"
zip -r twython-psycopg2.zip python 
sudo rm -rf python/ # delete not needed python file