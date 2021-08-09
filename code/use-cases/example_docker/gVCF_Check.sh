#!/bin/bash


# Set var
inp=$1
chrom=$2
acc=$(basename ${inp} | sed 's/.g.vcf.gz//g')
base=$(basename ${inp})


# Sanity check gVCF
iid=$(zcat ${inp} | head -n 10000 | grep "#CHROM" | cut -f 10)
size=$(du -sh ${inp} | awk '{print $1}')
length=$(tabix ${inp} -R ${tgt} | wc -l)
width=$(zcat ${inp} | grep -v "\#" | awk '{print NF}' | sort | uniq -c | awk '{print $2}' | xargs | sed 's/ /,/g')
NVar=$(tabix ${inp} -R ${tgt} | grep -c "MQ")


# Summarise all
# GQ20=$(tabix ${inp} -R ${tgt} | grep -v "MQ" | cut -f 10 | cut -d \: -f 4 | sort -n | awk '$1 > 20 {print}' | wc -l)
# GQ60=$(tabix ${inp} -R ${tgt} | grep -v "MQ" | cut -f 10 | cut -d \: -f 4 | sort -n | awk '$1 > 60 {print}' | wc -l)
# GQ90=$(tabix ${inp} -R ${tgt} | grep -v "MQ" | cut -f 10 | cut -d \: -f 4 | sort -n | awk '$1 > 90 {print}' | wc -l)
# genomeSummary=${GQ20},${GQ60},${GQ90}


# Summarise variants
GQ20=$(tabix ${inp} -R ${tgt} | grep "MQ" | cut -f 10 | cut -d \: -f 4 | sort -n | awk '$1 > 20 {print}' | wc -l)
GQ60=$(tabix ${inp} -R ${tgt} | grep "MQ" | cut -f 10 | cut -d \: -f 4 | sort -n | awk '$1 > 60 {print}' | wc -l)
GQ90=$(tabix ${inp} -R ${tgt} | grep "MQ" | cut -f 10 | cut -d \: -f 4 | sort -n | awk '$1 > 90 {print}' | wc -l)
variantSummary=${GQ20},${GQ60},${GQ90}


# Create table
# echo -e "IID\\tAccession\\tgVCF\\tDisk_Usage\\tWidth\\tLength\\tN_Variants\\tGenome_GQ_Summary(GT_20,GT_60,GT_90)\\tVariant_GQ_Summary(GT_20,GT_60,GT_90)" > ${acc}_checks.tsv
echo -e "${chrom}\\t${width}\\t${length}\\t${NVar}\\t${variantSummary}" > ${acc}_checks.tsv
