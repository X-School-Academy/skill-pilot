```bash
sudo add-apt-repository ppa:ubuntuhandbook1/coturn
sudo apt update
sudo apt install coturn

# That command adds or updates a long-term user in the database.
sudo turnadmin -a -u myuser -r your-domain-or-server-name -p mypassword

sudo systemctl restart coturn
sudo systemctl status coturn
```

```json
{
  "urls": ["turn:your-server:3478?transport=udp", "turn:your-server:3478?transport=tcp"],
  "username": "myuser",
  "credential": "mypassword"
}
```
MuseTalk pip install:

aiohttp
aiortc
dotenv

```bash
python -m scripts.live_chat --avatar frank --port 8008 --fps 12 --driver openai
ssh -L 21938:192.168.1.222:8008 local-dev
# http://127.0.0.1:21938/
```
MuseTalk/data/video/frank.mp4
cd MuseTalk/data/silent/frank
fmpeg -i ../../video/frank.mp4 frame_%03d.png