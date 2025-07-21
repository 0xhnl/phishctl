import argparse
import requests
from datetime import datetime, timezone
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


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


def get_id_by_name(endpoint, name, host, headers):
    response = requests.get(f"{host}/api/{endpoint}/", headers=headers, verify=False)
    if response.status_code == 200:
        for item in response.json():
            if item["name"] == name:
                return item["id"]
    return None


def create_campaign(campaign_name, template_name, landing_page_name, url, profile_name, group_name, send_now, host, api_key):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    template_id = get_id_by_name("templates", template_name, host, headers)
    if not template_id:
        print(f"[-] Template '{template_name}' not found.")
        return

    landing_page_id = get_id_by_name("pages", landing_page_name, host, headers)
    if not landing_page_id:
        print(f"[-] Landing page '{landing_page_name}' not found.")
        return

    profile_id = get_id_by_name("smtp", profile_name, host, headers)
    if not profile_id:
        print(f"[-] Sending profile '{profile_name}' not found.")
        return

    group_id = get_id_by_name("groups", group_name, host, headers)
    if not group_id:
        print(f"[-] Group '{group_name}' not found.")
        return

    launch_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if send_now else "2099-12-31T00:00:00Z"
    print(f"[+] Launching campaign at: {launch_date}")

    data = {
        "name": campaign_name,
        "template": {"name": template_name, "id": template_id},
        "page": {"name": landing_page_name, "id": landing_page_id},
        "url": url,
        "smtp": {"name": profile_name, "id": profile_id},
        "launch_date": launch_date,
        "groups": [{"name": group_name, "id": group_id}]
    }

    response = requests.post(f"{host}/api/campaigns/", headers=headers, json=data, verify=False)
    if response.status_code == 201:
        print(f"[+] Successfully created campaign: {campaign_name}")
    else:
        print(f"[-] Failed to create campaign: {campaign_name}")
        print(f"    Response: {response.text}")


def main():
    creds = load_credentials()
    host = creds["GOPHISH_HOST"]
    api_key = creds["API_KEY"]

    parser = argparse.ArgumentParser(description="Create and start a phishing campaign in GoPhish.")
    parser.add_argument("-l", "--landing-page", required=True, help="Name of the landing page")
    parser.add_argument("-t", "--template", required=True, help="Name of the email template")
    parser.add_argument("-u", "--url", required=True, help="Campaign URL (redirect URL)")
    parser.add_argument("-p", "--profile", required=True, help="Sending profile name")
    parser.add_argument("-g", "--group", required=True, help="Target group name")
    parser.add_argument("-c", "--campaign", required=True, help="Campaign name")
    parser.add_argument("-now", action="store_true", help="Send the campaign immediately")

    args = parser.parse_args()

    create_campaign(
        campaign_name=args.campaign,
        template_name=args.template,
        landing_page_name=args.landing_page,
        url=args.url,
        profile_name=args.profile,
        group_name=args.group,
        send_now=args.now,
        host=host,
        api_key=api_key
    )


if __name__ == "__main__":
    main()
