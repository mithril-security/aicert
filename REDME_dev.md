# Requirements 


The server requires access to /dev/tpmrm0, so 
for testing at least you'll need to run `sudo chmod 0666 /dev/tpmrm0`


Install git-lfs

curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash
sudo apt-get install git-lfs
git lfs install

```
sudo apt-get update
sudo apt-get install libtss2-dev
```

# Dependencies needed for tpm2-pytss 
sudo apt-get install pkg-config tpm2-tools


```
cd server
poetry shell
```

Run test

```
pytest server/main.py
```