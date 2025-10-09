#!/usr/bin/env python3
"""
Create ENA taxonomy request TSV file from taxonomy check & GBIF results.

This script processes taxonomy validation results and creates a properly formatted
TSV file for submission to the European Nucleotide Archive (ENA) for taxonomy ID creation.
It specifically handles cases where taxonomy IDs could not be matched and need to be
requested to be created by ENA.
"""

import sys
import pandas as pd
import argparse
import os


def read_file_agnostic(filepath):
    """
    Read a file that could be CSV, TSV, or Excel format.
    Returns a pandas DataFrame.
    """
    _, ext = os.path.splitext(filepath.lower())
    
    try:
        if ext in ['.xlsx', '.xls']:
            df = pd.read_excel(filepath)
        elif ext == '.tsv':
            df = pd.read_csv(filepath, sep='\t')
        else:  # Default to CSV
            df = pd.read_csv(filepath)
        
        return df
    except Exception as e:
        print(f"Error reading file {filepath}: {e}", file=sys.stderr)
        sys.exit(1)


def create_taxid_request(taxid_check_file, gbif_results_file, output_file):
    """
    Create ENA taxonomy request TSV file.
    
    Args:
        taxid_check_file (str): Path to the taxonomy check CSV file
        gbif_results_file (str): Path to the GBIF results file (CSV/TSV/Excel)
        output_file (str): Path for the output TSV file
    """
    # Read input files
    print(f"Reading taxonomy check file: {taxid_check_file}")
    taxid_df = pd.read_csv(taxid_check_file)
    
    print(f"Reading GBIF results file: {gbif_results_file}")
    gbif_df = read_file_agnostic(gbif_results_file)
    
    # Validate required columns
    required_taxid_cols = ['Process ID', 'taxid_match', 'species', 'genus']
    missing_taxid_cols = [col for col in required_taxid_cols if col not in taxid_df.columns]
    if missing_taxid_cols:
        print(f"Error: Missing required columns in taxid_check file: {missing_taxid_cols}", file=sys.stderr)
        sys.exit(1)
    
    required_gbif_cols = ['process_id', 'gbif_link']
    missing_gbif_cols = [col for col in required_gbif_cols if col not in gbif_df.columns]
    if missing_gbif_cols:
        print(f"Error: Missing required columns in gbif_results file: {missing_gbif_cols}", file=sys.stderr)
        sys.exit(1)
    
    # Filter rows where taxid_match == "FALSE" (handle various formats)
    filtered_df = taxid_df[taxid_df['taxid_match'].astype(str).str.strip().str.upper() == "FALSE"].copy()    
    print(f"Found {len(filtered_df)} rows with taxid_match == FALSE")
    
    if len(filtered_df) == 0:
        print("No rows to process. Exiting.")
        sys.exit(0)
    
    # Initialize output columns
    output_rows = []
    
    # Process each row
    for idx, row in filtered_df.iterrows():
        process_id = row['Process ID']
        species = str(row['species']).strip()
        genus = str(row['genus']).strip()
        
        # Determine name_type and proposed_name
        if species.lower() == 'not collected' or species == '' or pd.isna(row['species']):
            # Novel species case
            name_type = 'novel_species'
            proposed_name = f"{genus} sp. {process_id}"
        else:
            # Published name case
            name_type = 'published_name'
            proposed_name = species
        
        # Get description from GBIF results file
        gbif_match = gbif_df[gbif_df['process_id'] == process_id]
        if not gbif_match.empty:
            description = str(gbif_match.iloc[0]['gbif_link'])
            # Handle NaN or empty values
            if description == 'nan' or pd.isna(gbif_match.iloc[0]['gbif_link']):
                description = ''
        else:
            description = ''
            print(f"Warning: No GBIF result found for Process ID {process_id}")
        
        # Create output row
        output_row = {
            'proposed_name': proposed_name,
            'name_type': name_type,
            'host': '',
            'project_id': 'Biodiversity Genomics Europe',
            'description': description
        }
        
        output_rows.append(output_row)
    
    # Create output DataFrame
    output_df = pd.DataFrame(output_rows)
    
    # Write to TSV file
    output_df.to_csv(output_file, sep='\t', index=False)
    print(f"\nSuccessfully created taxonomy request file: {output_file}")
    print(f"Total entries: {len(output_df)}")
    print(f"  - Published names: {len(output_df[output_df['name_type'] == 'published_name'])}")
    print(f"  - Novel species: {len(output_df[output_df['name_type'] == 'novel_species'])}")


def main():
    parser = argparse.ArgumentParser(
        description="Create ENA taxonomy request TSV file from taxonomy check results."
    )
    parser.add_argument(
        '--taxid_check',
        required=True,
        help="Path to the taxonomy check CSV file"
    )
    parser.add_argument(
        '--gbif_results',
        required=True,
        help="Path to the GBIF results file (CSV/TSV/Excel format)"
    )
    parser.add_argument(
        '-o', '--output',
        required=True,
        help="Path for the output TSV file"
    )
    
    args = parser.parse_args()
    
    # Validate input files exist
    if not os.path.exists(args.taxid_check):
        print(f"Error: taxid_check file not found: {args.taxid_check}", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.exists(args.gbif_results):
        print(f"Error: gbif_results file not found: {args.gbif_results}", file=sys.stderr)
        sys.exit(1)
    
    create_taxid_request(args.taxid_check, args.gbif_results, args.output)


if __name__ == "__main__":
    main()
