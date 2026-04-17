#!/usr/bin/env python3
"""
Lädt alle geänderten Dateien direkt über die GitHub API hoch.
Nutzt den Browser-Session-Cookie um sich zu authentifizieren.
"""
import os
import base64
import json
import requests

# GitHub API Token aus Umgebung oder Browser-Session
# Wir nutzen die GitHub API mit dem Token aus den Browser-Cookies
REPO = "renerush1988/nhm-coach"
BRANCH = "main"

# Dateien die hochgeladen werden sollen
FILES = [
    "database.py",
    "assistant.py", 
    "main.py",
    "requirements.txt",
    "templates/assistant.html",
    "templates/base.html",
    "static/css/style.css",
]

def get_file_sha(token, filepath):
    """Holt den SHA eines bestehenden Files."""
    url = f"https://api.github.com/repos/{REPO}/contents/{filepath}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json().get("sha")
    return None

def upload_file(token, filepath, local_path):
    """Lädt eine Datei über die GitHub API hoch."""
    with open(local_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")
    
    sha = get_file_sha(token, filepath)
    
    url = f"https://api.github.com/repos/{REPO}/contents/{filepath}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    
    data = {
        "message": f"feat: KI-Assistent - update {filepath}",
        "content": content,
        "branch": BRANCH,
    }
    if sha:
        data["sha"] = sha
    
    r = requests.put(url, headers=headers, json=data)
    if r.status_code in (200, 201):
        print(f"✅ {filepath}")
        return True
    else:
        print(f"❌ {filepath}: {r.status_code} - {r.text[:200]}")
        return False

if __name__ == "__main__":
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("❌ GITHUB_TOKEN nicht gesetzt")
        exit(1)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    for filepath in FILES:
        local_path = os.path.join(base_dir, filepath)
        if os.path.exists(local_path):
            upload_file(token, filepath, local_path)
        else:
            print(f"⚠️  Datei nicht gefunden: {local_path}")
    
    print("\nFertig!")
