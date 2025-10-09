# ENA Taxonomic Identifier (TaxID) validation and request workflow
A three script pipeline for validating current taxonomic identifiers against NCBI (using TaxonKit) and ENA taxonomy databases, retrieving GBIF metadata, and generating ENA taxonomy request files for specimens without species-level TaxIDs.

## Overview
This workflow processes taxonomic data through three sequential scripts:
1. **GBIF metadata retrieval and species validation** (`01_run_check_gbif_ids.R`) - Queries GBIF for taxonomic information
2. **Check 01_gbif_results.xlsx and manually update filtered sample_metadata.csv** - Manually check outcome of GBIF taxonomy and metadata retrieval, and update as necessary
3. **Taxonomic ID validation** (`02_taxid_check.py`) - Validates taxonomic IDs using TaxonKit and ENA databases
4. **ENA request generation** (`03_request_generator.py`) - Creates properly formatted TSV files for ENA taxonomic ID requests

## Prerequisites
### Conda environment
- Create from ena_taxid.yaml:
  ```bash
  conda env create -f ena_taxid.yaml
  ```
### TaxonKit Database
```bash
# Download and decompress NCBI taxdump
wget -c [ftp://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz](https://ftp.ncbi.nih.gov/pub/taxonomy/new_taxdump/new_taxdump.tar.gz)
tar -zxvf new_taxdump.tar.gz
# Remove all .dmp files, other than names.dmp, nodes.dmp, delnodes.dmp, and merged.dmp
```

## Input file requirements
The initial input file can easily be created from the BGE sample_metadata.csv file using the `filter_csv.py` script, or manually. It must contain at minimum these columns (supported formats = CSV, TSV, or XLSX):
- `Process ID` - Unique identifier for each sample
- `species` - Species name (use "not collected" for unknown species)
- `genus` - Genus name (required if species is "not collected")
- Additional taxonomic columns: `phylum`, `class`, `order`, `family` (optional but recommended)
```
# filter_csv.py usage:
    python filter_csv.py --csv [input_csv] --txt [input_txt] --filter [csv column to filter on] --output [output_csv]

--csv = Input CSV file containing (at least) the columns above
--txt = Input text file with filter values (one per line). For example, a list of Process IDs to filter/extract from input CSV file
--filter = Column name to filter on (e.g., "Process ID")
--output = Output CSV file path
```


## Workflow Steps
### Step 1: GBIF metadata retrieval and species validation
Queries the GBIF database for taxonomic information and metadata.
- Input = CSV file with taxonomic data (such as output by filter_csv.py)
- Output = Excel file with GBIF results, including process_id (from input CSV), taxa ('species' from input CSV), gbif_id (GBIF TaxonIDs), gbif_key (GBIF key), id_key_match (TRUE/FALSE comparison of gbif_id and gbif_key), authorship (from GBIF record), accepted_name (taxon name in GBIF), taxa_accepted_name_match (TRUE/FALSE comparison of input taxa name and GBIF accepted_name), lineage (from GBIF record), and gbif_link (to species page), reference (supporting literature reference, if found).

```bash
# Edit 01_run_check_gbif_ids.R to specify your input/output files and paths
# Then run:
Rscript 01_run_check_gbif_ids.R
```

Example configuration in 01_run_check_gbif_ids.R:
```R
get_gbifid_out(
  csv_file = "./path/to/your_input_data.csv", 
  out_file = "./path/to/01_gbif_results.xlsx"
)
```


### Step 2: Check 01_gbif_results.xlsx and manually update filtered sample_metadata.csv
- Check if 'id_key_match' and/or 'taxa_accepted_name_match' == FALSE for any sample.
- Validate correct GBIF identifier (id or key) and correct taxon name (taxa or accepted_name) in [GBIF](https://www.gbif.org/species/search?q=).
- Manually update 'species' column for those samples that require it.



### Step 3: Taxonomic ID validation
Validates taxonomic IDs using both TaxonKit (NCBI taxonomy) and ENA taxonomy databases (searches ENA for exact matches in scientific names and synonyms).
- Input = Original CSV/TSV/XLSX file with (updated) taxonomic data from step 2
- Output =
    - `02_taxid_check.csv` - Full results with TaxonKit (NCBI) and ENA TaxIDs (if found). Input CSV + additional columns (taxonkit_name (Name matched by TaxonKit), taxonkit_taxid (NCBI taxonomy ID from TaxonKit), taxonkit_lookup_warning (Any warnings), ena_scientificName (Scientific name from ENA), ena_TaxId (ENA taxonomic ID), taxid_match (TRUE/FALSE/EMPTY))
    - `02_no_taxids.csv` - Rows where both TaxonKit and ENA failed to find a TaxID
    - `02_check_taxids.log` - \Script processing log
```bash
python 02_taxid_check.py --input sample_metadata-updated.csv --data-dir ~/new_taxdump/
```
- `taxid_match` - Comparison result:
  - `TRUE` - Both TaxIDs present and match
  - `FALSE` - ENA TaxID missing OR TaxIDs don't match
  - Empty - TaxonKit TaxID missing but ENA has value


### Step 4: ENA TaxID request generation
Creates a properly formatted TSV file for submitting taxonomic ID requests to ENA.
- Input = 
    - `02_taxid_check.csv` from Step 3
    - `01_gbif_results.xlsx` from Step 1
- Output = TSV file formatted for ENA taxonomic ID creation request
```bash
python 03_request_generator.py --taxid_check 02_taxid_check.csv --gbif_results 01_gbif_results.xlsx -o ena_taxonomy_request.tsv
```

**Output format:**
| Column | Description |
|--------|-------------|
| `proposed_name` | Species name or novel species designation |
| `name_type` | `published_name` or `novel_species` |
| `host` | Host organism (empty by default) |
| `project_id` | Project identifier (default: "Biodiversity Genomics Europe") |
| `description` | GBIF link as evidence of valid speces concept |

**Logic:**
- Processes only rows where `taxid_match == "FALSE"` (i.e. where a TaxID was not found in ENA, or TaxIDs between TaxonKit (NCBI) and ENA do not match)
- For known species: uses `published_name` type with species name
- For unknown species: uses `novel_species` type with format `[Genus] sp. [Process ID]`


## Complete Workflow Example
```bash
# Step 1: Get GBIF metadata
Rscript 01_run_check_gbif_ids.R

# Step 2: Validate taxonomy IDs
python 02_taxid_check.py --input your_samples.csv --data-dir ~/taxonkit_db

# Step 3: Generate ENA request file
python 03_request_generator.py --taxid_check 02_taxid_check.csv --gbif_results 01_gbif_results.xlsx -o ena_taxonomy_request.tsv
```

## Authors
- Dan Parsons, Maria Kamouyiaros & Ben Price @NHMUK
