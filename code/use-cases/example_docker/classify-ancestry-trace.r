#!/usr/bin/Rscript --slave --silent --vanilla


# Load libraries
# print("Loading libraries")
library("rpart")


# Parse args
args <- commandArgs(trailingOnly = TRUE)
data <- args[1]
eu_model <- args[2]
out <- args[3]
wrk = dirname(data)
setwd(wrk)
# print(args)


# Load model and data
# print("Loading model")
eu_model <- readRDS(eu_model)
data <- read.delim(data, sep = "\t", quote = "", header = TRUE)


# Parse sampleIDs and PC1-4
# print("Performing Classification")
head(data[ , c(2,3,4,5)])
data$Prediction <- predict(object = eu_model, data[ , c(2,3,4,5)], type = "class")
write.table(data, file = out, quote = FALSE, sep = "\t", col.names = TRUE, row.names = FALSE)
