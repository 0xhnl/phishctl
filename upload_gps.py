import os
import csv
import argparse
import requests

# Disable SSL warnings
import urllib3
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
        print(f"Error loading credentials from {config_path}: {e}")
        exit(1)

    if "GOPHISH_HOST" not in creds or "API_KEY" not in creds:
        print("Missing GOPHISH_HOST or API_KEY in creds.conf.")
        exit(1)

    return creds


def upload_group(file_path, host, api_key):
    group_name = os.path.basename(file_path).replace(".csv", "")
    users = []

    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "Email" in row and row["Email"].strip():
                    users.append({
                        "email": row["Email"].strip(),
                        "first_name": row.get("First Name", "").strip(),
                        "last_name": row.get("Last Name", "").strip()
                    })
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return

    if not users:
        print(f"No valid users found in {file_path}")
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {"name": group_name, "targets": users}

    try:
        response = requests.post(f"{host}/api/groups/?api_key={api_key}", headers=headers, json=payload, verify=False)
        response.raise_for_status()
        print(f"[+] Successfully uploaded group: {group_name}")
    except requests.exceptions.RequestException as e:
        print(f"[-] Failed to upload {group_name}: {e}")


def process_folder(folder_path, host, api_key):
    if not os.path.isdir(folder_path):
        print(f"Invalid folder: {folder_path}")
        return

    for file in os.listdir(folder_path):
        if file.endswith(".csv"):
            upload_group(os.path.join(folder_path, file), host, api_key)


def main():
    creds = load_credentials()
    host = creds["GOPHISH_HOST"]
    api_key = creds["API_KEY"]

    parser = argparse.ArgumentParser(description="Upload CSV users to GoPhish")
    parser.add_argument("-f", "--file", help="Single CSV file to upload")
    parser.add_argument("-ff", "--folder", help="Folder containing multiple CSV files")
    args = parser.parse_args()

    if args.file:
        upload_group(args.file, host, api_key)
    elif args.folder:
        process_folder(args.folder, host, api_key)
    else:
        print("Please specify either a file (-f) or a folder (-ff)")


if __name__ == "__main__":
    main()
