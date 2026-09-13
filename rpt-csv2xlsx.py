#!/usr/bin/env python3
"""Combine Gophish campaign CSV exports into a single Excel workbook.

Produces five sheets:

  * Summary          - one row per campaign with Sent/Opened/Clicked/Submitted
                       counts and rates, plus a TOTAL row.
  * Email Sent       - every target the email was sent to (cumulative funnel).
  * Email Opened     - targets who opened, clicked, or submitted (cumulative).
  * Link Clicked     - targets who clicked or submitted (cumulative).
  * Credential Submit- one row per unique submission, keeping the captured
                       credential fields as submitted.

Input files:
  <campaign>_results.csv    Gophish per-target results (one per campaign).
  <campaign>_submitted.csv  Gophish captured submissions (optional per campaign).
"""
import pandas as pd
import argparse
import glob
import os
import re

# Gophish records only the latest status per target, so the funnel is
# cumulative: a target that submitted data was also sent, opened, and clicked.
# Each funnel sheet therefore includes its own status plus every status further
# down the funnel.
FUNNEL_SHEETS = [
    ("Email Sent",    ["Email Sent", "Email Opened", "Clicked Link", "Submitted Data"]),
    ("Email Opened",  ["Email Opened", "Clicked Link", "Submitted Data"]),
    ("Link Clicked",  ["Clicked Link", "Submitted Data"]),
]

# The Credential Submit sheet corresponds to this status.
SUBMIT_STATUS = "Submitted Data"

# Columns kept from *_results.csv ('id' is Gophish's per-target id -> 'rid').
RESULT_COLUMNS = ['campaign', 'id', 'email', 'status', 'ip',
                  'latitude', 'longitude', 'send_date']

# Layout of the Email Sent / Email Opened / Link Clicked sheets.
FUNNEL_COLUMNS = ['campaign', 'scenario', 'email', 'rid', 'ip',
                  'latitude', 'longitude', 'send_date']

# Identity columns placed first on the Credential Submit sheet; every remaining
# captured field (passwords, username, corporate_mail, ...) follows dynamically.
SUBMITTED_LEAD = ['campaign', 'scenario', 'email', 'rid', 'ip', 'submitted_time']
SUBMITTED_TRAIL = ['user-agent']


def load_scenarios(input_folder):
    """Best-effort map of campaign -> scenario, parsed from command-to-send.md.

    Looks in the input folder and its parent. Returns {} when not found so the
    scenario column simply stays blank.
    """
    candidates = [
        os.path.join(input_folder, 'command-to-send.md'),
        os.path.join(input_folder, os.pardir, 'command-to-send.md'),
    ]
    path = next((p for p in candidates if os.path.isfile(p)), None)
    if not path:
        return {}

    with open(path, encoding='utf-8') as fh:
        text = fh.read()

    mapping = {}
    # Each `create_camp.py ...` block carries one -c "<campaign>" and -t "<template>".
    for block in text.split('create_camp.py')[1:]:
        camp = re.search(r'-c\s+"([^"]+)"', block)
        tmpl = re.search(r'-t\s+"([^"]+)"', block)
        if camp and tmpl:
            mapping[camp.group(1)] = tmpl.group(1)
    return mapping


def load_results(input_folder):
    all_files = sorted(glob.glob(os.path.join(input_folder, "*_results.csv")))
    if not all_files:
        print("No *_results.csv files found in the folder.")
        return None

    dfs = []
    for file in all_files:
        campaign = re.sub(r'_results\.csv$', '', os.path.basename(file))
        try:
            df = pd.read_csv(file)
        except Exception as e:
            print(f"Error reading {file}: {e}")
            continue

        df.insert(0, 'campaign', campaign)
        dfs.append(df[[col for col in RESULT_COLUMNS if col in df.columns]])
        print(f"Loaded {campaign}: {len(df)} records")

    if not dfs:
        print("No valid campaign results CSV files found.")
        return None

    combined = pd.concat(dfs, ignore_index=True)
    return combined.rename(columns={'id': 'rid'})


def load_submitted(input_folder):
    all_files = sorted(glob.glob(os.path.join(input_folder, "*_submitted.csv")))
    dfs = []
    for file in all_files:
        campaign = re.sub(r'_submitted\.csv$', '', os.path.basename(file))
        try:
            df = pd.read_csv(file)
        except Exception as e:
            print(f"Error reading {file}: {e}")
            continue
        if df.empty:
            continue
        df.insert(0, 'campaign', campaign)
        dfs.append(df)

    if not dfs:
        return None
    return pd.concat(dfs, ignore_index=True)


def build_summary(combined, scenarios):
    rows = []
    for campaign, grp in combined.groupby('campaign', sort=True):
        status = grp['status']
        sent = len(grp)
        opened = status.isin(["Email Opened", "Clicked Link", "Submitted Data"]).sum()
        clicked = status.isin(["Clicked Link", "Submitted Data"]).sum()
        submitted = (status == "Submitted Data").sum()
        rows.append({
            'campaign': campaign,
            'scenario': scenarios.get(campaign, ''),
            'sent': sent,
            'opened': opened,
            'clicked': clicked,
            'submitted': submitted,
            'open_rate': f"{opened / sent:.1%}" if sent else "0.0%",
            'click_rate': f"{clicked / sent:.1%}" if sent else "0.0%",
            'submit_rate': f"{submitted / sent:.1%}" if sent else "0.0%",
        })

    summary = pd.DataFrame(rows)
    totals = {
        'campaign': 'TOTAL',
        'scenario': '',
        'sent': summary['sent'].sum(),
        'opened': summary['opened'].sum(),
        'clicked': summary['clicked'].sum(),
        'submitted': summary['submitted'].sum(),
    }
    total_sent = totals['sent']
    totals['open_rate'] = f"{totals['opened'] / total_sent:.1%}" if total_sent else "0.0%"
    totals['click_rate'] = f"{totals['clicked'] / total_sent:.1%}" if total_sent else "0.0%"
    totals['submit_rate'] = f"{totals['submitted'] / total_sent:.1%}" if total_sent else "0.0%"
    return pd.concat([summary, pd.DataFrame([totals])], ignore_index=True)


def build_funnel(combined, scenarios, statuses):
    stage = combined[combined['status'].isin(statuses)].copy()
    stage['scenario'] = stage['campaign'].map(scenarios).fillna('')
    stage = stage.sort_values(['campaign', 'email'])
    return stage.reindex(columns=FUNNEL_COLUMNS)


def mask_password(value):
    """Mask a captured password, revealing only the first two and last two
    characters and replacing everything in between with '*' (e.g.
    'Yomacreditcard@35' -> 'Yo*************35'). Values of four characters or
    fewer are fully masked so short secrets are never exposed. Blank/NaN values
    are left untouched.
    """
    if value is None:
        return value
    s = str(value)
    if s == '' or s.lower() == 'nan':
        return value
    n = len(s)
    if n <= 4:
        return '*' * n
    return s[:2] + '*' * (n - 4) + s[-2:]


# Any captured column whose name contains 'password' is masked on the
# Credential Submit sheet (password, current_password, new_password,
# confirm_password, ...).
def _mask_password_columns(df):
    for col in df.columns:
        if 'password' in str(col).lower():
            df[col] = df[col].map(mask_password)
    return df


def build_submitted(submitted, combined, scenarios):
    # Prefer the captured submissions (they carry the credential fields). Fall
    # back to the results rows so the sheet still lists submitters even when no
    # *_submitted.csv files were exported.
    if submitted is None:
        stage = combined[combined['status'] == SUBMIT_STATUS].copy()
        stage['scenario'] = stage['campaign'].map(scenarios).fillna('')
        stage = stage.sort_values(['campaign', 'email'])
        return stage.reindex(columns=FUNNEL_COLUMNS)

    submitted = submitted.copy()
    submitted = submitted.rename(columns={'time': 'submitted_time'})

    # Collapse repeated submissions by the same target to the latest one, so the
    # count matches the 'Submitted Data' funnel stage.
    if 'rid' in submitted.columns:
        if 'submitted_time' in submitted.columns:
            submitted = submitted.sort_values('submitted_time')
        before = len(submitted)
        submitted = submitted.drop_duplicates(subset=['campaign', 'rid'], keep='last')
        dropped = before - len(submitted)
        if dropped:
            print(f"Deduplicated {dropped} repeat submission(s)")

    submitted['scenario'] = submitted['campaign'].map(scenarios).fillna('')

    # Mask captured passwords before they reach the workbook.
    submitted = _mask_password_columns(submitted)

    # Lead identity columns, then any captured fields, then user-agent last.
    known = set(SUBMITTED_LEAD) | set(SUBMITTED_TRAIL)
    captured = [c for c in submitted.columns if c not in known]
    ordered = ([c for c in SUBMITTED_LEAD if c in submitted.columns]
               + captured
               + [c for c in SUBMITTED_TRAIL if c in submitted.columns])
    return submitted.reindex(columns=ordered)


def autosize(worksheet, df):
    worksheet.freeze_panes = 'A2'
    for idx, col in enumerate(df.columns, start=1):
        width = len(str(col))
        lengths = df[col].dropna().astype(str).str.len()
        if len(lengths):
            width = max(width, int(lengths.max()))
        worksheet.column_dimensions[
            worksheet.cell(row=1, column=idx).column_letter
        ].width = min(width + 2, 60)


def write_sheet(writer, name, df):
    df.to_excel(writer, sheet_name=name, index=False)
    autosize(writer.sheets[name], df)
    print(f"Added sheet '{name}' with {len(df)} records")


def combine_csv_to_excel(input_folder, output_file):
    combined = load_results(input_folder)
    if combined is None:
        return
    if 'status' not in combined.columns:
        print("Error: no 'status' column found in the results CSV files.")
        return

    scenarios = load_scenarios(input_folder)
    submitted = load_submitted(input_folder)

    if submitted is None:
        print("No *_submitted.csv files found; 'Credential Submit' will list "
              "submitters from the results without captured credential fields")

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        write_sheet(writer, 'Summary', build_summary(combined, scenarios))
        for sheet_name, statuses in FUNNEL_SHEETS:
            write_sheet(writer, sheet_name, build_funnel(combined, scenarios, statuses))
        write_sheet(writer, 'Credential Submit',
                    build_submitted(submitted, combined, scenarios))

    print(f"Combined {len(combined)} target records into {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Combine Gophish campaign CSV results into one Excel file with "
                    "Summary / Email Sent / Email Opened / Link Clicked / "
                    "Credential Submit sheets."
    )
    parser.add_argument("-ff", "--folder", required=True, help="Folder containing CSV files")
    parser.add_argument("-o", "--output", required=True, help="Output Excel file path")
    args = parser.parse_args()

    combine_csv_to_excel(args.folder, args.output)
