import json
import urllib.request
import urllib.error
import zipfile
import os
import sys

MISSING_PACKAGES = [
    "altair==6.2.2",
    "blinker==1.9.0",
    "cachetools==7.1.4",
    "deprecation==2.1.0",
    "gitdb==4.0.12",
    "GitPython==3.1.50",
    "h2==4.3.0",
    "hpack==4.2.0",
    "httptools==0.8.0",
    "hyperframe==6.1.0",
    "itsdangerous==2.2.0",
    "pillow==12.2.0",
    "postgrest==2.31.0",
    "pyarrow==24.0.0",
    "pydeck==0.9.2",
    "PyJWT==2.13.0",
    "python-multipart==0.0.32",
    "realtime==2.31.0",
    "smmap==5.0.3",
    "starlette==1.3.1",
    "storage3==2.31.0",
    "streamlit==1.58.0",
    "StrEnum==0.4.15",
    "supabase==2.31.0",
    "supabase-auth==2.31.0",
    "supabase-functions==2.31.0",
    "toml==0.10.2",
    "uvicorn==0.49.0"
]

SITE_PACKAGES = "/Users/layc/Documents/hoa_auditor_kaggle-submission/.venv/lib/python3.14/site-packages"

def get_wheel_url(pkg_name, version):
    api_url = f"https://pypi.org/pypi/{pkg_name}/{version}/json"
    print(f"Fetching PyPI info for {pkg_name}=={version}...")
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Error fetching JSON for {pkg_name}: {e}")
        return None
    
    urls = data.get("urls", [])
    wheels = [u for u in urls if u["packagetype"] == "bdist_wheel"]
    
    for w in wheels:
        filename = w["filename"].lower()
        if "cp314" in filename and ("arm64" in filename or "universal2" in filename or "macosx" in filename):
            return w["url"], w["filename"]
            
    for w in wheels:
        filename = w["filename"].lower()
        if "py3-none-any" in filename or "py2.py3-none-any" in filename:
            return w["url"], w["filename"]

    for w in wheels:
        filename = w["filename"].lower()
        if "macosx" in filename and ("arm64" in filename or "universal2" in filename):
            if "abi3" in filename or "py3" in filename:
                return w["url"], w["filename"]
            if "cp314" in filename:
                return w["url"], w["filename"]
                
    if wheels:
        return wheels[0]["url"], wheels[0]["filename"]
        
    return None, None

def run_sync(pkg_spec):
    pkg_name, version = pkg_spec.split("==")
    url, filename = get_wheel_url(pkg_name, version)
    if not url:
        print(f"No wheel found for {pkg_spec}")
        return False
        
    print(f"Downloading {filename}...")
    local_path = os.path.join("/Users/layc/Documents/hoa_auditor_kaggle-submission", filename)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response, open(local_path, "wb") as out_file:
            out_file.write(response.read())
    except Exception as e:
        print(f"Failed to download {filename}: {e}")
        return False
        
    print(f"Extracting to {SITE_PACKAGES}...")
    try:
        with zipfile.ZipFile(local_path, "r") as zip_ref:
            zip_ref.extractall(SITE_PACKAGES)
        print(f"Done {pkg_spec}")
        os.remove(local_path)
        return True
    except Exception as e:
        print(f"Failed to extract {filename}: {e}")
        if os.path.exists(local_path):
            os.remove(local_path)
        return False

def main():
    success_count = 0
    failed_pkgs = []
    for pkg in MISSING_PACKAGES:
        if run_sync(pkg):
            success_count += 1
        else:
            failed_pkgs.append(pkg)
            
    print(f"Result: {success_count}/{len(MISSING_PACKAGES)}")
    if failed_pkgs:
        print(f"Failed: {failed_pkgs}")

if __name__ == "__main__":
    main()
