library(stringr)
library(dplyr)
library(taxize)
library(tools)
library(writexl)

# Function to pull gbif metadata from taxonomic name
get_gbifid_out <- function(csv_file, out_file){
  
  df <- read.csv(csv_file, header = T)
  
  # NEW: Use genus when species is "not collected"
  taxa <- ifelse(tolower(trimws(as.character(df$species))) == "not collected" | 
                 trimws(as.character(df$species)) == "" | 
                 is.na(df$species),
                 as.vector(df$genus),
                 as.vector(df$species))
  
  process_ids <- as.vector(df$Process.ID)
  
  gbiftaxID <- data.frame(process_id=process_ids, taxa=taxa, gbif_id=rep(NA,length(taxa)))
  
  cat(paste0("Processing ", length(taxa), " species...\n"))
  
  for(i in 1:length(taxa)){
    
    cat(paste0("Processing ", i, "/", length(taxa), ": ", gbiftaxID$taxa[i], "\n"))
    
    if(length(gbif_name_usage(name = gbiftaxID$taxa[i])$results) > 0 && length(gbif_name_usage(name = gbiftaxID$taxa[i])$results[[1]]$species) > 0){
      gbiftaxID$gbif_id[i] <- gbif_name_usage(name = gbiftaxID$taxa[i])$results[[1]]$taxonID
      gbiftaxID$gbif_key[i] <- gbif_name_usage(name = gbiftaxID$taxa[i])$results[[1]]$key
      gbiftaxID$authorship[i] <- gbif_name_usage(name = gbiftaxID$taxa[i])$results[[1]]$authorship
      gbiftaxID$accepted_name[i] <- gbif_name_usage(name = gbiftaxID$taxa[i])$results[[1]]$species
      gbiftaxID$lineage[i] <- paste(gbif_name_usage(name = gbiftaxID$taxa[i])$results[[1]]$kingdom,
                                    gbif_name_usage(name = gbiftaxID$taxa[i])$results[[1]]$phylum,
                                    gbif_name_usage(name = gbiftaxID$taxa[i])$results[[1]]$order,
                                    gbif_name_usage(name = gbiftaxID$taxa[i])$results[[1]]$family,
                                    gbif_name_usage(name = gbiftaxID$taxa[i])$results[[1]]$genus,
                                    gbif_name_usage(name = gbiftaxID$taxa[i])$results[[1]]$species,
                                    sep = ";")
      gbiftaxID$gbif_link[i] <- paste0("https://www.gbif.org/species/", gbif_name_usage(name = gbiftaxID$taxa[i])$results[[1]]$key)
    }else{
      gbiftaxID$gbif_id[i] <- NA
      gbiftaxID$gbif_key[i] <- NA
      gbiftaxID$accepted_name[i] <- NA
      gbiftaxID$authorship[i] <- NA
      gbiftaxID$lineage[i] <- NA
      gbiftaxID$gbif_link[i] <- NA
    }
    if(length(gbif_name_usage(name = gbiftaxID$taxa[i])$results) >0 && length(gbif_name_usage(name = gbiftaxID$taxa[i])$results[[1]]$publishedIn)>0) {
      gbiftaxID$reference[i] <- gbif_name_usage(name = gbiftaxID$taxa[i])$results[[1]]$publishedIn
    }else{
      gbiftaxID$reference[i] <- NA
    }
  }
  
  # Add comparison column for gbif_id vs gbif_key - strip "gbif:" prefix before comparing
  gbiftaxID$id_key_match <- ifelse(is.na(gbiftaxID$gbif_id) | is.na(gbiftaxID$gbif_key), 
                                   NA, 
                                   gsub("^gbif:", "", as.character(gbiftaxID$gbif_id)) == as.character(gbiftaxID$gbif_key))
  
  # Add comparison column for taxa vs accepted_name
  gbiftaxID$taxa_accepted_name_match <- ifelse(is.na(gbiftaxID$taxa) | is.na(gbiftaxID$accepted_name), 
                                               NA, 
                                               as.character(gbiftaxID$taxa) == as.character(gbiftaxID$accepted_name))
  
  # Column reordering
  gbiftaxID <- gbiftaxID %>%
    select(process_id, taxa, gbif_id, gbif_key, id_key_match, authorship, accepted_name, taxa_accepted_name_match, everything())
  
  cat("Writing output file...\n")
  writexl::write_xlsx(unique(gbiftaxID), out_file)
  cat("Done!\n")
  
}



### Usage across files
#filelist <- list.files(pattern = "_Lichen_Tracking_Sheet_null_taxids.csv")
#f<-1
#for(f in 1:length(filelist)){
#  fbase <- tools::file_path_sans_ext(filelist[f])
#  fout <- paste0(fbase, "_gbif.xlsx")
#  
#  get_gbifid_out(csv_file = filelist[f], out_file=fout)
#}
