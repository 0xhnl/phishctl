# 📧 phishctl

A lightweight command-line toolkit for automating GoPhish operations:

- ✅ Generate email recipient CSV files
- ✅ Upload user groups to GoPhish
- ✅ Launch phishing campaigns

# 📁 Project Structure

```bash
.
├── mail_gen.py         # Split emails into multiple CSVs for campaigns
├── upload_gps.py       # Upload CSV groups to GoPhish
├── create_camp.py      # Create and launch campaigns
├── pusher-puller.py    # Pull/Push templates and landing pages
├── creds.conf          # Configuration file (GoPhish host and API key)
└── output/             # Output CSVs from mail_gen.py
```

# 🛠️ Step 0: Sync Templates & Landing Pages (pusher-puller.py)

Before launching campaigns, you can manage your email templates and landing pages locally:

```bash
# Pull all templates
python3 pusher-puller.py -t -pull

# Push updated templates
python3 pusher-puller.py -t -push

# Pull all landing pages
python3 pusher-puller.py -l -pull

# Push updated landing pages
python3 pusher-puller.py -l -push
```

| Flag   | Description                                |
| ------ | ------------------------------------------ |
| `-t`   | Target Templates (folder: templates/)      |
| `-l`   | Target Landing Pages (folder: landing/)    |
| `-pull`| Download from server                       |
| `-push`| Sync local changes to server               |
| `--dir`| (Optional) Override default folder path    |


# 🔐 Step 1: Setup creds.conf

- Create a file named creds.conf in the root directory:

```bash
GOPHISH_HOST=https://your-gophish-host:3333
API_KEY=your-api-key-here
```

- Replace your-gophish-host with your GoPhish instance.
- Replace your-api-key-here with your actual API key from GoPhish UI.

# ✉️ Step 2: Generate Email CSVs (mail_gen.py)

- A .txt file with one email per line.

```bash
python3 mail_gen.py -i emails.txt -c 100
```

- 📂 Creates output like:

```txt
output/
├── G01.csv
├── G02.csv
└── ...
```

# ⬆️ Step 3: Upload Groups to GoPhish (upload_gps.py)

- Upload all generated CSVs to GoPhish as user groups:

```bash
# Upload a single file
python3 upload_gps.py -f output/G01.csv

# Upload all csvs in a folder
python3 upload_gps.py -ff output/
```

# 🎯 Step 4: Launch a Campaign (create_camp.py)

- Create and optionally launch a GoPhish campaign using previously uploaded groups:

```bash
python3 create_camp.py \
  -c "HR Policy Test" \
  -t "Policy Template" \
  -l "Policy Landing" \
  -u "http://intranet.company.com" \
  -p "Internal SMTP" \
  -g "G01" \
  -now
```

| Flag   | Description                          |
| ------ | ------------------------------------ |
| `-c`   | Campaign name                        |
| `-t`   | Email template name                  |
| `-l`   | Landing page name                    |
| `-u`   | Redirect URL                         |
| `-p`   | Sending profile name (SMTP)          |
| `-g`   | Target group name (uploaded earlier) |
| `-now` | (Optional) Launch immediately        |

# 📄 Step 5: Report Parsing

- Make sure to download all campaign results CSV and place in one folder.

```bash
$ python3 rpt-csv2xlsx.py -ff results -o campaign-results.xlsx
```

# ⚠️ Warnings

- SSL cert warnings are disabled by default (verify=False) in scripts. For production, you should enable SSL verification.
- Do not hardcode your API key in scripts. Always use creds.conf.
