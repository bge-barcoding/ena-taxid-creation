# ENA Taxonomy Request File Generator
A Python script for processing taxonomic data and generating properly formatted taxonomy request files for the European Nucleotide Archive (ENA). This tool specialises in handling cases where species-level taxonomy IDs are not available, and uses IDs from the [GBIF Backbone taxonomy](https://www.gbif.org/dataset/d7dddbf4-2cf0-4f39-9b2a-bb099caae36c), fetched using the [GBIF Species API](https://techdocs.gbif.org/en/openapi/v1/species) to support requests to ENA.

## Features
- Processes taxonomic metadata from CSV files
- Validates scientific names against GBIF taxonomy - checks name existence and spelling, taxonomic status (accepted/synonym), match confidence (>95% for species / >90% for genus), and match type (exact/fuzzy), as per GBIF guidlines.
- Implements hierarchical fallback for taxonomic identification (uses species name if available, otherwise falls back to "Genus sp. {process_id}" if only genus is available, or "Family sp. {process_id}" if only family is available.
- Performs taxonomic rank validation of returned GBIF taxonomy against provided taxonomy (validates taxonomy at order and class ranks).
- Handles synonyms and taxonomic updates
- Generates ENA-compliant taxonomy request files (see below).

## Prerequisites
- Python 3.6+
- Required Python packages:
  - pandas
  - pygbif
  - logging

## Installation
1. Clone this repository:
```bash
git clone [repository-url]
```
2. Install required packages, e.g. pandas and [pygbif](https://github.com/gbif/pygbif)
```bash
pip install pandas pygbif
```

## Usage
```
python ena_taxonomy_request.py path/to/sample_metadata.csv path/to/samples.csv output_prefix
```

## Input files
- **metadata.csv**: Contains columns:
  - Process ID
  - phylum
  - class
  - order
  - family
  - genus
  - species
  - matched_rank
  - taxid

- **samples.csv**: Contains columns:
  - ID (i.e. Process ID)

## Output Files
The script generates several output files with the specified prefix:
- {prefix}_taxonomy_request.tsv: Main output file formatted for ENA submission
- {prefix}_tax_validation_fails.csv: Records that failed taxonomic validation
- {prefix}_gbif_inconsistent.tsv: Records with GBIF inconsistencies (synonyms, etc.)
- {prefix}.log: Detailed processing log

### Example {prefix}_taxonomy_request.tsv
| proposed_name  | name_type | host | project_id | description |
| --------- | --------- |--------- | --------- | --------- |
| Apatania stylata  | published_name |  | BGE | https://www.gbif.org/species/[GBIF ID] | 
| Agapetus iridipennis | published_name |  | BGE | https://www.gbif.org/species/[GBIF ID] | 
| Papomyia sp. BSNHM191-24 | novel_species |  | BGE | https://www.gbif.org/species/[GBIF ID] | 

### Example {prefix}_gbif_inconsistent.tsv
| usageKey |	scientificName |	canonicalName |	rank |	status |	confidence |	matchType |	kingdom |	phylum | order |	family |	genus |	species |	kingdomKey |	phylumKey |	classKey |	orderKey |	familyKey |	genusKey |	speciesKey |	synonym |	class |	index	| acceptedUsageKey |
| --- |	--- |	--- |	--- |	--- |	--- |	--- |	--- |	--- | --- |	--- |	--- |	--- |	--- |	--- |	--- |	--- |	--- |	--- |	--- |	--- |	--- |	---	| --- |
| 8753555	| Erotesis melanella McLachlan, 1884 | Erotesis melanella	| SPECIES	| SYNONYM	| 98	| EXACT	| Animalia	| Arthropoda |	Trichoptera |	Leptoceridae |	Adicella |	Adicella melanella |	1 |	54 |	216 | 1003	| 4395	| 1436670	| 1436745	| True |	Insecta	| 5	| 1436745 |

  - Erotesis melanella McLachlan, 1884 == [8753555](https://www.gbif.org/species/8753555)
  - Adicella melanella (McLachlan, 1884) == [1436745](https://www.gbif.org/species/1436745)

## Authors
- Dan Parsons @NHMUK
