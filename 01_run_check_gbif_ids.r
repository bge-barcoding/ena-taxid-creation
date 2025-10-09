#!/usr/bin/env Rscript

# Source the function
source("check_gbif_ids.R")

# Run the function
get_gbifid_out(csv_file = "./path/to/input.csv", 
               out_file = "./path/to/output/01_gbif_results.xlsx")
