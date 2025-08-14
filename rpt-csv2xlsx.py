#!/usr/bin/env python3
import pandas as pd
import argparse
import glob
import os
import re

def combine_csv_to_excel(input_folder, output_file):
    all_files = glob.glob(os.path.join(input_folder, "*.csv"))
    if not all_files:
        print("No CSV files found in the folder.")
        return

    # Group files by campaign category (C or F)
    campaign_categories = {'C': [], 'F': []}
    for file in all_files:
        filename = os.path.basename(file)
        # Extract campaign type (C or F)
        match = re.match(r'^([CF])\d+_results\.csv$', filename)
        if match:
            category = match.group(1)
            if category in campaign_categories:
                campaign_categories[category].append(file)

    # Remove empty categories
    campaign_categories = {k: v for k, v in campaign_categories.items() if v}

    if not campaign_categories:
        print("No valid campaign CSV files found.")
        return

    # Create Excel writer
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Process each campaign category
        for category, files in campaign_categories.items():
            dfs = []
            print(f"Processing {len(files)} {category} campaign files...")

            for file in files:
                try:
                    df = pd.read_csv(file)

                    # Define the desired column order
                    desired_columns = ['id', 'email', 'status', 'ip', 'latitude', 'longitude', 'send_date']

                    # Keep only the desired columns that exist in the dataframe
                    existing_columns = [col for col in desired_columns if col in df.columns]
                    df = df[existing_columns]

                    dfs.append(df)
                except Exception as e:
                    print(f"Error reading {file}: {e}")

            if dfs:
                # Combine all files for this category
                combined_df = pd.concat(dfs, ignore_index=True)

                # Reorder columns to match desired order
                final_columns = [col for col in ['id', 'email', 'status', 'ip', 'latitude', 'longitude', 'send_date'] if col in combined_df.columns]
                combined_df = combined_df[final_columns]

                # Write to Excel sheet named after category
                combined_df.to_excel(writer, sheet_name=category, index=False)
                print(f"Added sheet '{category}' with {len(combined_df)} records")

    print(f"Combined files into {output_file} with {len(campaign_categories)} sheets")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Combine multiple CSV files into one Excel file with separate sheets for C and F campaigns.")
    parser.add_argument("-ff", "--folder", required=True, help="Folder containing CSV files")
    parser.add_argument("-o", "--output", required=True, help="Output Excel file path")
    args = parser.parse_args()

    combine_csv_to_excel(args.folder, args.output)
