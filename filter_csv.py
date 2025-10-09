#!/usr/bin/env python3
import argparse
import csv
import unicodedata

def normalise_string(s):
    """Remove all whitespace and hidden characters, convert to lowercase"""
    # Remove all whitespace characters (spaces, tabs, newlines, etc.)
    s = ''.join(s.split())
    # Remove other control/hidden characters
    s = ''.join(char for char in s if unicodedata.category(char)[0] != 'C')
    # Convert to lowercase for case-insensitive comparison
    return s.lower()

def main():
    parser = argparse.ArgumentParser(
        description='Filter CSV rows based on values in a text file'
    )
    parser.add_argument('--csv', required=True, help='Input CSV file')
    parser.add_argument('--output', required=True, help='Output CSV file')
    parser.add_argument('--txt', required=True, help='Text file with filter values (one per line)')
    parser.add_argument('--filter', required=True, help='Column name to filter on (e.g., "Process ID")')
    
    args = parser.parse_args()
    
    # Read filter values from txt file and normalise them
    with open(args.txt, 'r', encoding='utf-8') as f:
        filter_values = set(normalise_string(line) for line in f if line.strip())
    
    # Process CSV
    with open(args.csv, 'r', newline='', encoding='utf-8') as infile, \
         open(args.output, 'w', newline='', encoding='utf-8') as outfile:
        
        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
        
        # Write header
        writer.writeheader()
        
        # Filter and write rows
        matches = 0
        for row in reader:
            if normalise_string(row[args.filter]) in filter_values:
                writer.writerow(row)
                matches += 1
    
    print(f"Filtering complete. Found {matches} matching rows.")
    print(f"Output written to {args.output}")

if __name__ == '__main__':
    main()
