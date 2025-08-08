#!/usr/bin/env python3
import pandas as pd
import argparse
import glob
import os

def combine_csv_to_excel(input_folder, output_file):
    all_files = glob.glob(os.path.join(input_folder, "*.csv"))
    if not all_files:
        print("No CSV files found in the folder.")
        return

    dfs = []
    for file in all_files:
        try:
            df = pd.read_csv(file)
            # Drop unwanted columns if they exist
            cols_to_remove = ['first_name', 'last_name', 'position', 'modified_date', 'reported']
            df = df.drop(columns=[col for col in cols_to_remove if col in df.columns])
            df['source_file'] = os.path.basename(file)  # optional: track which file it came from
            dfs.append(df)
        except Exception as e:
            print(f"Error reading {file}: {e}")

    if dfs:
        combined_df = pd.concat(dfs, ignore_index=True)
        combined_df.to_excel(output_file, index=False)
        print(f"Combined {len(all_files)} files into {output_file}")
    else:
        print("No valid CSV data to combine.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Combine multiple CSV files into one Excel file.")
    parser.add_argument("-ff", "--folder", required=True, help="Folder containing CSV files")
    parser.add_argument("-o", "--output", required=True, help="Output Excel file path")
    args = parser.parse_args()

    combine_csv_to_excel(args.folder, args.output)
