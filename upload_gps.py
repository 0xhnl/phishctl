import os
import csv
import argparse
import requests
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def load_credentials(config_path="creds.conf"):
    creds = {}
    try:
        with open(config_path, "r") as f:
            for line in f:
                if line.strip() and not line.strip().startswith("#"):
                    key, value = line.strip().split("=", 1)
                    creds[key.strip()] = value.strip()
    except Exception as e:
        print(f"Error loading credentials: {e}")
        exit(1)
    return creds

def parse_txt(file_path):
    users = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            email = line.strip()
            if email:
                users.append({"email": email, "first_name": "", "last_name": ""})
    return users

def parse_csv(file_path):
    users = []
    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "Email" in row and row["Email"].strip():
                users.append({
                    "email": row["Email"].strip(),
                    "first_name": row.get("First Name", "").strip(),
                    "last_name": row.get("Last Name", "").strip()
                })
    return users

def upload_group(file_path, host, api_key, custom_name=None):
    file_ext = os.path.splitext(file_path)[1].lower()
    group_name = custom_name if custom_name else os.path.basename(file_path).replace(file_ext, "")
    
    users = []
    try:
        if file_ext == ".csv":
            users = parse_csv(file_path)
        elif file_ext == ".txt":
            users = parse_txt(file_path)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0

    if not users:
        return 0

    headers = {"Content-Type": "application/json"}
    payload = {"name": group_name, "targets": users}

    try:
        url = f"{host}/api/groups/?api_key={api_key}"
        response = requests.post(url, headers=headers, json=payload, verify=False)
        response.raise_for_status()
        print(f"[+] Successfully uploaded: {group_name} (from {os.path.basename(file_path)})")
        return len(users) # Return the count for the summary
    except requests.exceptions.RequestException as e:
        print(f"[-] Failed to upload {group_name}: {e}")
        return 0

def process_folder(folder_path, host, api_key):
    if not os.path.isdir(folder_path):
        print(f"Invalid folder: {folder_path}")
        return

    supported_exts = (".csv", ".txt")
    files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(supported_exts)])
    
    total_emails = 0
    for index, file_name in enumerate(files, start=1):
        g_name = f"G{index:02d}"
        file_path = os.path.join(folder_path, file_name)
        count = upload_group(file_path, host, api_key, custom_name=g_name)
        total_emails += count

    print("---")
    print(f"[*] Total uploaded mail count: {total_emails}")

def main():
    creds = load_credentials()
    host = creds.get("GOPHISH_HOST")
    api_key = creds.get("API_KEY")

    parser = argparse.ArgumentParser(description="Upload users to GoPhish")
    parser.add_argument("-f", "--file", help="Single file to upload")
    parser.add_argument("-ff", "--folder", help="Folder containing files")
    args = parser.parse_args()

    if args.file:
        count = upload_group(args.file, host, api_key, custom_name="G01")
        print(f"[*] Total uploaded mail count: {count}")
    elif args.folder:
        process_folder(args.folder, host, api_key)
    else:
        print("Please specify -f or -ff")

if __name__ == "__main__":
    main()
