import os
import sys
import pandas as pd
from pathlib import Path
import pathlib
import logging
import csv
import subprocess
import argparse
import requests
import urllib.parse
import time

# Configure logger - will be updated in main() to write to output directory
logger = logging.getLogger()
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)

def setup_logging(output_dir):
    """Set up file logging in the output directory"""
    log_file = os.path.join(output_dir, "02_check_taxids.log")
    file_handler = logging.FileHandler(log_file)
    logger.addHandler(file_handler)
    logger.info(f"Logging to: {log_file}")

def detect_delimiter(file_path):
    with open(file_path, 'r') as csvfile:
        dialect = csv.Sniffer().sniff(csvfile.read(1024))
        return dialect.delimiter

def read_file(file_path):
    # Check if the provided file exists
    if not Path(file_path).is_file():
        logger.error(f"Error: The file '{file_path}' does not exist.")
        sys.exit(1)
    
    # If the file is an XLSX read_excel, else read_csv
    if pathlib.Path(file_path).suffix == ".xlsx":
        df = pd.read_excel(file_path)
    else:
        delimiter = detect_delimiter(file_path)
        df = pd.read_csv(file_path, delimiter=delimiter)
    
    # Drop rows that are entirely empty
    df.dropna(how="all", inplace=True)
    return df

def prepare_taxon_names(df):
    """
    Prepare taxon names for TaxonKit lookup based on species/genus columns.
    Returns a list of taxon names and a list of warning flags for rows with issues.
    """
    taxon_names = []
    warning_flags = []
    
    for idx, row in df.iterrows():
        species_val = str(row.get('species', 'not collected')).strip()
        genus_val = str(row.get('genus', 'not collected')).strip()
        
        # Check if both are "not collected"
        if species_val == "not collected" and genus_val == "not collected":
            logger.warning(f"Row {idx}: Both species and genus are 'not collected'. Using 'MISSING_TAXON' placeholder.")
            taxon_names.append("MISSING_TAXON")
            warning_flags.append("WARNING: Both species and genus not collected")
        elif species_val != "not collected":
            taxon_names.append(species_val)
            warning_flags.append("")
        else:  # species is "not collected", use genus
            taxon_names.append(genus_val)
            warning_flags.append("")
    
    return taxon_names, warning_flags

def search_ena_taxonomy(species_name, logger):
    """
    Search ENA taxonomy database for a species name.
    Returns tuple: (scientific_name, tax_id, status_message)
    
    status_message can be:
    - None (successful match)
    - "API_ERROR: <error details>" 
    - "NO_MATCH"
    - "MULTIPLE_MATCHES_NO_EXACT"
    """
    if not species_name or species_name.lower() == 'not collected' or species_name == 'MISSING_TAXON':
        return None, None, None
    
    # URL encode the species name
    encoded_name = urllib.parse.quote(species_name)
    api_url = f'https://www.ebi.ac.uk/ena/taxonomy/rest/suggest-for-submission/{encoded_name}'
    
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Calling ENA API: {api_url}")
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            results = response.json()
            
            # No results found
            if not results:
                logger.info(f"No results found for '{species_name}'")
                return None, None, "NO_MATCH"
            
            logger.info(f"Found {len(results)} potential matches from ENA for '{species_name}'")
            
            # Search for exact match
            species_name_lower = species_name.lower()
            
            for taxon in results:
                # Check for direct match with scientificName
                if taxon.get('scientificName', '').lower() == species_name_lower:
                    logger.info(f"Found exact match in scientificName: {taxon.get('scientificName')}")
                    return taxon.get('scientificName'), taxon.get('taxId'), None
                
                # Check in otherNames for exact match
                other_names = taxon.get('otherNames', [])
                for other_name in other_names:
                    # Extract the name part before any colon
                    name_parts = other_name.split(':', 1)
                    other_name_clean = name_parts[0].strip()
                    
                    if other_name_clean.lower() == species_name_lower:
                        logger.info(f"Found exact match in otherNames: {other_name}")
                        return taxon.get('scientificName'), taxon.get('taxId'), None
            
            # If we get here, no exact match found
            logger.info(f"Multiple matches found but no exact match for '{species_name}'")
            return None, None, "MULTIPLE_MATCHES_NO_EXACT"
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                logger.warning(f"API request failed: {str(e)}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
            logger.error(f"API request failed after {max_retries} attempts: {str(e)}")
            return None, None, f"API_ERROR: {str(e)}"
        
        except (ValueError, KeyError) as e:
            logger.error(f"API response parsing error: {str(e)}")
            return None, None, f"API_ERROR: Response parsing error - {str(e)}"
    
    # Should not reach here, but just in case
    return None, None, "API_ERROR: Maximum retries exceeded"

def search_ena_for_species(df, logger):
    """
    Search ENA taxonomy for all species in the dataframe.
    Returns two lists: ena_scientific_names and ena_tax_ids
    Rate limited to 10 queries per second.
    """
    ena_scientific_names = []
    ena_tax_ids = []
    
    min_delay = 0.1  # 100ms = 10 queries per second
    last_request_time = 0
    
    for idx, row in df.iterrows():
        species_val = str(row.get('species', 'not collected')).strip()
        
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - last_request_time
        if time_since_last < min_delay:
            time.sleep(min_delay - time_since_last)
        
        last_request_time = time.time()
        
        # Search ENA
        sci_name, tax_id, status = search_ena_taxonomy(species_val, logger)
        
        # Handle results based on status
        if status is None:
            # Successful match
            ena_scientific_names.append(sci_name if sci_name else "")
            ena_tax_ids.append(tax_id if tax_id else "")
        elif status == "NO_MATCH":
            ena_scientific_names.append("")
            ena_tax_ids.append("")
        elif status == "MULTIPLE_MATCHES_NO_EXACT":
            ena_scientific_names.append("MULTIPLE_MATCHES_NO_EXACT")
            ena_tax_ids.append("")
            logger.warning(f"Row {idx}: Multiple matches found but no exact match for '{species_val}'")
        elif status.startswith("API_ERROR"):
            ena_scientific_names.append(status)
            ena_tax_ids.append("")
            logger.warning(f"Row {idx}: {status} for '{species_val}'")
        else:
            # Unknown status
            ena_scientific_names.append(f"UNKNOWN_ERROR: {status}")
            ena_tax_ids.append("")
    
    return ena_scientific_names, ena_tax_ids

def compare_taxids(merged_df):
    """
    Compare taxonkit_taxid and ena_TaxId columns.
    Returns a list with:
    - TRUE if both have values and they match
    - FALSE if ena_TaxId is empty OR if both have values and don't match
    - Empty string if taxonkit_taxid is empty but ena_TaxId has a value
    """
    taxid_match = []
    
    for idx, row in merged_df.iterrows():
        taxonkit_id = row.get('taxonkit_taxid', '')
        ena_id = row.get('ena_TaxId', '')
        
        # Convert to string, strip whitespace, and handle float conversions
        if pd.notna(taxonkit_id) and taxonkit_id != '':
            taxonkit_str = str(taxonkit_id).strip()
            # Remove .0 if it's a float representation of an integer
            if '.' in taxonkit_str:
                try:
                    taxonkit_str = str(int(float(taxonkit_str)))
                except (ValueError, OverflowError):
                    pass
        else:
            taxonkit_str = ''
        
        if pd.notna(ena_id) and ena_id != '':
            ena_str = str(ena_id).strip()
            # Remove .0 if it's a float representation of an integer
            if '.' in ena_str:
                try:
                    ena_str = str(int(float(ena_str)))
                except (ValueError, OverflowError):
                    pass
        else:
            ena_str = ''
        
        # If ena_TaxId is empty, write FALSE
        if ena_str == '':
            taxid_match.append('FALSE')
        # If taxonkit_taxid is empty but ena_TaxId has a value, leave empty
        elif taxonkit_str == '':
            taxid_match.append('')
        # If both have values and they match
        elif taxonkit_str == ena_str:
            taxid_match.append('TRUE')
        # If both have values and they don't match
        else:
            taxid_match.append('FALSE')
    
    return taxid_match

def merge_df(df, taxids_df, warning_flags, ena_scientific_names, ena_tax_ids, file_path):
    # Add warning flags column
    df['taxonkit_lookup_warning'] = warning_flags
    
    # Concatenate original df with taxonkit results
    merged_df = pd.concat([df, taxids_df], axis=1)
    
    # Add ENA results
    merged_df['ena_scientificName'] = ena_scientific_names
    merged_df['ena_TaxId'] = ena_tax_ids
    
    # Compare TaxIDs and add match column
    taxid_match = compare_taxids(merged_df)
    merged_df['taxid_match'] = taxid_match
    
    # Define output file path and save the merged dataframe
    filepath = os.path.dirname(file_path)
    outfile = os.path.join(filepath, "02_taxid_check.csv")

    merged_df.to_csv(outfile, sep=',', index=False)
    return outfile, merged_df

def save_no_taxid_rows(merged_df, file_path, logger):
    """
    Save rows where BOTH TaxonKit and ENA failed to find a TaxID.
    Only includes specified columns.
    """
    filepath = os.path.dirname(file_path)
    
    # Identify rows where both taxonkit_taxid and ena_TaxId are null/empty
    taxonkit_null = merged_df['taxonkit_taxid'].isna() | (merged_df['taxonkit_taxid'] == '')
    ena_null = merged_df['ena_TaxId'].isna() | (merged_df['ena_TaxId'] == '')
    
    both_null_mask = taxonkit_null & ena_null
    no_taxid_rows = merged_df[both_null_mask]
    
    if not no_taxid_rows.empty:
        logger.warning(f"Found {len(no_taxid_rows)} rows with no TaxID from both TaxonKit AND ENA")
        
        # Define the columns to include
        columns_to_include = [
            'Process ID', 'phylum', 'class', 'order', 'family', 'genus', 'species',
            'taxid', 'matched_rank', 'lineage', 'lineage_mismatch', 'taxonkit_lookup_warning',
            'taxonkit_name', 'taxonkit_taxid', 'ena_scientificName', 'ena_TaxId'
        ]
        
        # Filter to only include columns that exist in the dataframe
        available_columns = [col for col in columns_to_include if col in no_taxid_rows.columns]
        
        if len(available_columns) < len(columns_to_include):
            missing = set(columns_to_include) - set(available_columns)
            logger.warning(f"Some requested columns not found in dataframe: {missing}")
        
        no_taxid_subset = no_taxid_rows[available_columns]
        
        null_outfile = os.path.join(filepath, "02_no_taxids.csv")
        no_taxid_subset.to_csv(null_outfile, sep=',', index=False)
        logger.info(f"Rows with no TaxID from both sources saved to: {null_outfile}")
    else:
        logger.info("All rows have at least one TaxID (from either TaxonKit or ENA)")

def get_taxids(taxon_names, data_dir):
    """
    Get TaxIDs using TaxonKit and clean up temporary files.
    Returns a DataFrame with taxonkit_name and taxonkit_taxid columns.
    """
    temp_input = '02_taxon_names.txt'
    temp_output = '02_raw_takonkit_output.out'
    
    try:
        # Write taxon names to temporary file
        with open(temp_input, 'w') as f:
            f.write("\n".join(taxon_names))
        
        # Use taxonkit from conda environment with data-dir argument
        command = f"cat {temp_input} | taxonkit name2taxid --data-dir {data_dir} > {temp_output}"
        
        # Execute the shell command
        try:
            subprocess.run(command, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running taxonkit: {e}")
            sys.exit(1)
        
        # Read the generated output file
        taxids_df = pd.read_csv(temp_output, header=None, delimiter="\t", names=["taxonkit_name", "taxonkit_taxid"])
        
        return taxids_df
    
    finally:
        # Clean up temporary files
        for temp_file in [temp_input, temp_output]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    logger.info(f"Cleaned up temporary file: {temp_file}")
                except OSError as e:
                    logger.warning(f"Could not remove temporary file {temp_file}: {e}")

def main(file_path, data_dir):
    # Set up logging to output directory
    output_dir = os.path.dirname(file_path)
    setup_logging(output_dir)
    
    # Read the input file
    df = read_file(file_path)
    
    # Check required columns exist
    required_cols = ['species', 'genus']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.error(f"Missing required columns: {missing_cols}")
        sys.exit(1)
    
    # Prepare taxon names based on species/genus logic
    taxon_names, warning_flags = prepare_taxon_names(df)
    logger.info(f"Prepared {len(taxon_names)} taxon names for lookup")
    
    # Extract TaxIDs using taxonkit
    taxids_df = get_taxids(taxon_names, data_dir)
    logger.info(f"Extracted IDs from taxonkit")
    
    # Search ENA taxonomy database
    logger.info(f"Searching ENA taxonomy database (rate limited to 10 queries/second)...")
    ena_scientific_names, ena_tax_ids = search_ena_for_species(df, logger)
    logger.info(f"Completed ENA taxonomy search")
    
    # Merge data and write results to CSV
    output_filename, merged_df = merge_df(df, taxids_df, warning_flags, ena_scientific_names, ena_tax_ids, file_path)
    logger.info(f"CSV file '{output_filename}' created successfully.")
    
    # Save rows with no TaxID from BOTH sources
    save_no_taxid_rows(merged_df, file_path, logger)

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Get TaxIDs from taxonomic names using TaxonKit and ENA')
    parser.add_argument('--input', '--in', dest='input', required=True,
                        help='Input CSV/TSV/XLSX file path')
    parser.add_argument('--data-dir', dest='data_dir', required=True,
                        help='Directory containing TaxonKit database files (names.dmp, nodes.dmp, etc.)')
    
    args = parser.parse_args()
    
    # Verify data directory exists
    if not os.path.isdir(args.data_dir):
        logger.error(f"Error: Data directory '{args.data_dir}' does not exist.")
        sys.exit(1)
    
    # Call the main function with the arguments
    main(args.input, args.data_dir)
