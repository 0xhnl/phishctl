#!/usr/bin/env python3
import pandas as pd
import argparse
import glob
import os
import re

# Gophish stores only the latest status per target, so each funnel stage
# matches its own status plus every status further down the funnel.
STAGES = [
    ("Email Sent",        ["Email Sent", "Email Opened", "Clicked Link", "Submitted Data"]),
    ("Email Opened",      ["Email Opened", "Clicked Link", "Submitted Data"]),
    ("Email Clicked",     ["Clicked Link", "Submitted Data"]),
    ("Credential Submit", ["Submitted Data"]),
]

# Columns read from *_results.csv; 'id' is renamed to 'rid' after loading so it
# shares the same identifier column as the submitted-data sheet.
COLUMNS = ['campaign', 'id', 'email', 'status', 'ip', 'latitude', 'longitude', 'send_date']

# Layout of the funnel sheets (Email Sent / Opened / Clicked, Credential Submit).
FUNNEL_COLUMNS = ['campaign', 'rid', 'email', 'status', 'ip', 'latitude', 'longitude', 'send_date']

# Layout of the Submitted Data sheet. status/latitude/longitude/send_date are
# pulled from the results (Credential Submit) data by matching rid.
SUBMITTED_COLUMNS = ['campaign', 'rid', 'email', 'name', 'status', 'ip',
                     'latitude', 'longitude', 'send_date', 'Submitted Time', 'user-agent']

# Fields the Submitted Data sheet inherits from the results, keyed on rid.
ENRICH_COLUMNS = ['latitude', 'longitude', 'send_date']

# The Submitted Data sheet corresponds to the Credential Submit stage.
CRED_SUBMIT_LABEL = STAGES[-1][0]


def load_results(input_folder):
    all_files = sorted(glob.glob(os.path.join(input_folder, "*.csv")))
    if not all_files:
        print("No CSV files found in the folder.")
        return None

    dfs = []
    for file in all_files:
        filename = os.path.basename(file)
        match = re.match(r'^(.+)_results\.csv$', filename)
        if not match:
            continue
        campaign = match.group(1)

        try:
            df = pd.read_csv(file)
        except Exception as e:
            print(f"Error reading {file}: {e}")
            continue

        df.insert(0, 'campaign', campaign)
        dfs.append(df[[col for col in COLUMNS if col in df.columns]])
        print(f"Loaded {campaign}: {len(df)} records")

    if not dfs:
        print("No valid campaign CSV files found.")
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


def autosize(worksheet, df, columns):
    worksheet.freeze_panes = 'A2'
    for idx, col in enumerate(columns, start=1):
        width = len(str(col))
        if len(df):
            lengths = df[col].dropna().astype(str).str.len()
            if len(lengths):
                width = max(width, int(lengths.max()))
        worksheet.column_dimensions[
            worksheet.cell(row=1, column=idx).column_letter
        ].width = min(width + 2, 60)


def combine_csv_to_excel(input_folder, output_file, exact=False):
    combined = load_results(input_folder)
    if combined is None:
        return

    if 'status' not in combined.columns:
        print("Error: no 'status' column found in the CSV files.")
        return

    submitted = load_submitted(input_folder)
    if submitted is not None:
        # Pull status/latitude/longitude/send_date from the results, matched on rid.
        enrich = (combined[['campaign', 'rid'] + ENRICH_COLUMNS]
                  .drop_duplicates(subset=['campaign', 'rid']))
        submitted = submitted.drop(columns=[c for c in ENRICH_COLUMNS
                                            if c in submitted.columns])
        submitted = submitted.merge(enrich, on=['campaign', 'rid'], how='left')
        submitted['status'] = CRED_SUBMIT_LABEL
        submitted = submitted.rename(columns={'time': 'Submitted Time'})
        submitted = submitted.reindex(columns=SUBMITTED_COLUMNS)

    sheet_count = len(STAGES)

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        for sheet_name, statuses in STAGES:
            wanted = statuses[:1] if exact else statuses
            sheet_df = combined[combined['status'].isin(wanted)].reindex(columns=FUNNEL_COLUMNS).copy()
            # Label every row with this sheet's stage rather than the raw Gophish status.
            sheet_df['status'] = sheet_name
            sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)
            autosize(writer.sheets[sheet_name], sheet_df, FUNNEL_COLUMNS)
            print(f"Added sheet '{sheet_name}' with {len(sheet_df)} records")

        if submitted is not None:
            submitted.to_excel(writer, sheet_name='Submitted Data', index=False)
            autosize(writer.sheets['Submitted Data'], submitted, SUBMITTED_COLUMNS)
            sheet_count += 1
            print(f"Added sheet 'Submitted Data' with {len(submitted)} records")
        else:
            print("No *_submitted.csv files found; skipping 'Submitted Data' sheet")

    print(f"Combined {len(combined)} records into {output_file} with {sheet_count} sheets")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Combine Gophish campaign CSV results into one Excel file with "
                    "Email Sent / Email Opened / Email Clicked / Credential Submit sheets."
    )
    parser.add_argument("-ff", "--folder", required=True, help="Folder containing CSV files")
    parser.add_argument("-o", "--output", required=True, help="Output Excel file path")
    parser.add_argument("--exact", action="store_true",
                        help="Match each sheet's literal status only, instead of cumulative funnel stages")
    args = parser.parse_args()

    combine_csv_to_excel(args.folder, args.output, exact=args.exact)
