#!/usr/bin/env python3

import requests
import csv
import os
import sys
import argparse
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

def load_config(config_file='creds.conf'):
    """Load Gophish host and API key from config file"""
    config = {}
    try:
        with open(config_file, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    config[key] = value
    except FileNotFoundError:
        print(f"Error: Config file '{config_file}' not found")
        sys.exit(1)
    return config

def get_campaigns(api_url, api_key):
    """Fetch all campaigns from Gophish"""
    headers = {'Authorization': f'Bearer {api_key}'}
    response = requests.get(f"{api_url}/api/campaigns/", headers=headers, verify=False)
    response.raise_for_status()
    return response.json()

def get_campaign_results(api_url, api_key, campaign_id):
    """Fetch results for a specific campaign"""
    headers = {'Authorization': f'Bearer {api_key}'}
    response = requests.get(f"{api_url}/api/campaigns/{campaign_id}", headers=headers, verify=False)
    response.raise_for_status()
    return response.json()

def save_to_csv(data, filename):
    """Save campaign results to CSV file"""
    if not data:
        print(f"No data to write for {filename}")
        return

    # Normalize fieldnames (handle nested objects)
    fieldnames = set()
    for entry in data:
        for key in entry.keys():
            fieldnames.add(key)

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=sorted(fieldnames))
        writer.writeheader()
        for entry in data:
            # Flatten nested objects for CSV
            flat_entry = {}
            for key, value in entry.items():
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        flat_entry[f"{key}.{subkey}"] = subvalue
                else:
                    flat_entry[key] = value
            writer.writerow(flat_entry)

def main():
    parser = argparse.ArgumentParser(description='Download Gophish campaign results as CSV')
    parser.add_argument('-o', '--output', required=True, help='Output directory')
    args = parser.parse_args()

    # Load configuration from default creds.conf file
    config = load_config('creds.conf')
    api_url = config.get('GOPHISH_HOST', '').rstrip('/')
    api_key = config.get('API_KEY', '')

    if not api_url or not api_key:
        print("Error: GOPHISH_HOST or API_KEY not found in creds.conf")
        sys.exit(1)

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    try:
        # Get all campaigns
        campaigns = get_campaigns(api_url, api_key)
        print(f"Found {len(campaigns)} campaigns")

        for campaign in campaigns:
            campaign_id = campaign['id']
            campaign_name = campaign['name'].replace('/', '_').replace('\\', '_')
            print(f"Processing campaign: {campaign_name} (ID: {campaign_id})")

            # Get detailed results
            details = get_campaign_results(api_url, api_key, campaign_id)

            # Save only results (no events)
            results_filename = os.path.join(args.output, f"{campaign_name}_results.csv")
            save_to_csv(details.get('results', []), results_filename)

        print(f"Successfully saved campaign results to {args.output}")

    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
