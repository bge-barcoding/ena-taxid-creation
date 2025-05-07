# ENA Taxonomy Request File Generator
A Python script for processing taxonomic data and generating properly formatted taxonomy request files for the European Nucleotide Archive (ENA). This tool specialises in handling cases where species-level taxonomy IDs are not available, and uses IDs from the [GBIF Backbone taxonomy](https://www.gbif.org/dataset/d7dddbf4-2cf0-4f39-9b2a-bb099caae36c), fetched using the [GBIF Species API](https://techdocs.gbif.org/en/openapi/v1/species) to support requests to ENA.

## Features
- Processes taxonomic metadata from CSV files
- Validates scientific names against GBIF taxonomy
- Implements hierarchical fallback for taxonomic identification (uses species name if available, otherwise falls back to "Genus sp. {process_id}" if only genus is available, or "Family sp. {process_id}" if only family is available.
- Performs taxonomic rank validation 
- Handles synonyms and taxonomic updates
- Generates ENA-compliant taxonomy request files (see below).

## Logic
- Matches Process ID's in samples.csv with those in metadata.csv (as a sample filtering step).
- For those that match with matched_rank (in metadata.csv) == 'species' aren't processed further (they have a species-level taxid).
- For those that match with matched_rank != 'species', process these samples.
- Take the lowest available input taxonomic name for each sample to be processed and search in GBIF (using pygbif).
- Perform taxonomic rank validation of returned GBIF taxonomy against provided taxonomy (validates taxonomy at order, class and phyla ranks). If failed validation, output sample to tax_validation_fails.csv
- If passed validation, determine if search taxonomic name and GBIF taxonomy meet the following criteria:
```
- Has status "ACCEPTED"
- Has match type "EXACT"
- Has a confidence score >95% (species) or >90% (genus)
- Has a valid binomial name (<genus> <species>) or is a novel species (<genus> sp.)
```
- If valid, fetch GBIF ID, check record is in GBIF Taxonomy Backbone, and if so, output sample to taxonomy_request.tsv.
- If not valid or not in GBIF Taxonomy Backbone, fetch GBIF information and output sample to gbif_inconsistent.tsv for manual checking.

INTEGRATE UPDATED SEARCHING LOGIC
Step 1: name_backbone with strict=False
pythonresult = species.name_backbone(name='Solieria pacifica', strict=False)

name_backbone tries to match a name against the GBIF backbone taxonomy (their master taxonomic reference)
Setting strict=False allows it to match against higher classification levels if no direct match is found
This is typically faster and more precise, but can sometimes miss matches that would appear on the GBIF website
For Solieria pacifica, this might initially return a "matchType=NONE" result

Step 2: Fall back to species.search() (which is name_lookup)
pythonspecies_search_results = species.search(q='Solieria pacifica', limit=5)

The search function (which calls name_lookup) is a more comprehensive fuzzy search
It searches across ALL taxonomies in GBIF, not just the backbone
This is closer to how the GBIF website search works
It can find matches even when name_backbone fails
For Solieria pacifica, this would find both the plant and insect versions

Step 3: Get detailed information with species.name_usage()
pythonif first_match.get('key'):
    species_details = species.name_usage(key=first_match.get('key'))

Once we have a match and its key (unique ID) from name_lookup, we use name_usage to get complete details
name_usage retrieves full taxonomic information about that specific taxon
This gives us all the hierarchical data needed (phylum, class, order, etc.) for validation
For Solieria pacifica, this would return complete taxonomic details for validation
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
python ena_taxonomy_request.py -m/--metadata <path/to/sample_metadata.csv> -s/--samples <path/to/samples.csv> -op/--out_prefix <output_prefix>
```

## Input files
- **metadata.csv**: Must contain columns:
  - Process ID
  - phylum
  - class
  - order
  - family
  - genus
  - species
  - matched_rank
  - taxid

- **samples.csv**: Must contain columns:
  - ID (i.e. Process ID)

## Output Files
The script generates several output files into an output directory with the specified prefix:
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
