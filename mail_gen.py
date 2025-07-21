import argparse
import csv
import os

def split_emails_to_csv(input_file, chunk_size):
    # Read emails from the input file
    with open(input_file, 'r') as f:
        emails = [line.strip() for line in f if line.strip()]

    # Calculate the number of chunks
    total_emails = len(emails)
    num_chunks = (total_emails // chunk_size) + (1 if total_emails % chunk_size > 0 else 0)

    # Ensure the output directory exists
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    # Split emails into chunks and write to CSV files
    for i in range(num_chunks):
        start_index = i * chunk_size
        end_index = min((i + 1) * chunk_size, total_emails)
        chunk_emails = emails[start_index:end_index]

        # Generate CSV filename
        csv_filename = os.path.join(output_dir, f"G{str(i + 1).zfill(2)}.csv")

        # Write to CSV
        with open(csv_filename, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            # Write header
            csv_writer.writerow(["First Name", "Last Name", "Email", "Position"])
            # Write email rows
            for email in chunk_emails:
                csv_writer.writerow(["", "", email, ""])

        print(f"Created {csv_filename} with {len(chunk_emails)} emails.")

    print(f"Total {num_chunks} CSV files created in '{output_dir}' directory.")

def main():
    parser = argparse.ArgumentParser(description="Split emails into CSV files.")
    parser.add_argument("-i", "--input", required=True, help="Input file containing emails (one per line).")
    parser.add_argument("-c", "--chunk", type=int, required=True, help="Number of emails per CSV file.")
    
    args = parser.parse_args()

    if args.chunk <= 0:
        print("Error: Chunk size must be greater than 0.")
        return

    split_emails_to_csv(args.input, args.chunk)

if __name__ == "__main__":
    main()
