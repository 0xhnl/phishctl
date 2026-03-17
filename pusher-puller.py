import os
import requests
import json
import urllib3
import glob
import argparse
import sys

# Suppress insecure request warnings if using self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def load_creds(filepath):
    creds = {}
    try:
        with open(filepath, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    creds[key] = value
    except FileNotFoundError:
        print(f"Error: Credentials file not found at {filepath}")
        sys.exit(1)
    return creds

def sanitize_name(name):
    """Consistent sanitization for filenames."""
    return name.replace('/', '_').replace(' ', '_')

def pull_resources(host, headers, resource_type, target_dir):
    """Generic pull logic for templates or pages."""
    config = {
        'templates': {'endpoint': '/api/templates/'},
        'pages': {'endpoint': '/api/pages/'}
    }
    
    settings = config[resource_type]
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        print(f"Created directory: {target_dir}")

    url = f"{host}{settings['endpoint']}"
    try:
        print(f"Fetching {resource_type} from {url}...")
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        
        resources = response.json()
        print(f"Found {len(resources)} {resource_type}.")

        for res in resources:
            name = sanitize_name(res.get('name', 'unnamed'))
            html_content = res.get('html', '')
            
            filename = f"{name}.html"
            filepath = os.path.join(target_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"Saved: {filepath}")

    except Exception as e:
        print(f"Error pulling {resource_type}: {e}")

def push_resources(host, headers, resource_type, target_dir):
    """Generic push logic for templates or pages."""
    config = {
        'templates': {'endpoint': '/api/templates/'},
        'pages': {'endpoint': '/api/pages/'}
    }
    
    settings = config[resource_type]
    
    if not os.path.exists(target_dir):
        print(f"Error: Directory '{target_dir}' not found.")
        return

    # 1. Fetch existing resources to map sanitized name -> remote resource
    url = f"{host}{settings['endpoint']}"
    try:
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        remote_resources = response.json()
    except Exception as e:
        print(f"Error fetching remote {resource_type} for sync: {e}")
        return

    resource_map = {sanitize_name(res['name']): res for res in remote_resources}

    # 2. Iterate through local HTML files
    local_files = glob.glob(os.path.join(target_dir, "*.html"))
    if not local_files:
        print(f"No .html files found in {target_dir} directory.")
        return

    for filepath in local_files:
        filename = os.path.basename(filepath)
        sanitized_filename = filename[:-5] # Remove .html
        
        with open(filepath, 'r', encoding='utf-8') as f:
            html_content = f.read()

        if sanitized_filename in resource_map:
            # UPDATE
            remote_res = resource_map[sanitized_filename]
            rid = remote_res['id']
            payload = remote_res.copy()
            payload['html'] = html_content
            
            update_url = f"{url}{rid}"
            print(f"Updating {resource_type}: {remote_res['name']} (ID: {rid})...")
            try:
                res = requests.put(update_url, headers=headers, data=json.dumps(payload), verify=False)
                res.raise_for_status()
                print(f"Successfully updated '{remote_res['name']}'.")
            except Exception as e:
                print(f"Failed to update '{remote_res['name']}': {e}")
        else:
            # CREATE
            resource_name = sanitized_filename
            print(f"Creating new {resource_type}: {resource_name}...")
            
            if resource_type == 'templates':
                payload = {
                    "name": resource_name,
                    "subject": "New Template - Edit Subject",
                    "html": html_content,
                    "text": "New Template - Edit Text"
                }
            else: # pages
                payload = {
                    "name": resource_name,
                    "html": html_content,
                    "capture_credentials": True,
                    "capture_passwords": True,
                    "redirect_url": "https://google.com"
                }
                
            try:
                res = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)
                res.raise_for_status()
                print(f"Successfully created '{resource_name}'.")
            except Exception as e:
                print(f"Failed to create '{resource_name}': {e}")

def main():
    parser = argparse.ArgumentParser(description='GoPhish Manager')
    parser.add_argument('-t', action='store_true', help='Target templates (default directory: templates/)')
    parser.add_argument('-l', action='store_true', help='Target landing pages (default directory: landing/)')
    parser.add_argument('-pull', action='store_true', help='Pull resources from server')
    parser.add_argument('-push', action='store_true', help='Push resources to server')
    parser.add_argument('--dir', type=str, help='Override default directory')
    
    args = parser.parse_args()

    if not (args.t or args.l):
        print("Error: -t (templates) or -l (landing pages) flag is required.")
        parser.print_help()
        sys.exit(1)

    if not (args.pull or args.push):
        print("Error: Either -pull or -push must be specified.")
        parser.print_help()
        sys.exit(1)

    # Determine script path to find creds.conf nearby
    script_dir = os.path.dirname(os.path.realpath(__file__))
    creds_path = os.path.join(script_dir, 'creds.conf')
    
    # Load credentials
    creds = load_creds(creds_path)
    host = creds.get('GOPHISH_HOST', '').rstrip('/')
    api_key = creds.get('API_KEY', '')

    if not host or not api_key:
        print("Error: GOPHISH_HOST or API_KEY missing in creds.conf")
        sys.exit(1)

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    if args.t:
        target_dir = args.dir if args.dir else 'templates'
        if args.pull:
            pull_resources(host, headers, 'templates', target_dir)
        if args.push:
            push_resources(host, headers, 'templates', target_dir)
    
    if args.l:
        target_dir = args.dir if args.dir else 'landing'
        if args.pull:
            pull_resources(host, headers, 'pages', target_dir)
        if args.push:
            push_resources(host, headers, 'pages', target_dir)

if __name__ == "__main__":
    main()
