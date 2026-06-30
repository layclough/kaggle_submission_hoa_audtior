import sys

def check():
    # Try using pkg_resources or packaging/importlib
    try:
        import pkg_resources
    except ImportError:
        pkg_resources = None

    with open("requirements.txt") as f:
        reqs = f.read().splitlines()
    
    missing = []
    for req in reqs:
        req = req.strip()
        if not req or req.startswith("#"):
            continue
        parts = req.split("==")
        pkg_name = parts[0].strip()
        ver = parts[1].strip() if len(parts) > 1 else None
        
        try:
            # simple import check or pkg_resources check
            if pkg_resources:
                pkg_resources.require(req)
            else:
                __import__(pkg_name.lower().replace("-", "_"))
        except Exception as e:
            missing.append(req)
            print(f"Missing or mismatched: {req} ({e})")
            
    print(f"\nTotal missing: {len(missing)}")
    for m in missing:
        print(f"  {m}")

if __name__ == "__main__":
    check()
