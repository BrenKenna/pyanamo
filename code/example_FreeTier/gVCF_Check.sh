#!/bin/bash


# Set var
. ${TMPDIR}/start.sh
inp=$1
acc=$(basename ${inp} | cut -d \. -f 1)
base=$(basename ${inp})


# Sanity check gVCF dimensions + consistency
iid=$(zcat ${inp} | head -n 10000 | grep "^#CHROM" | cut -f 10)
size=$(du -sh ${inp} | awk '{print $1}')
length=$(${TABIX} ${inp} -R ${tgt} | wc -l)
width=$(zcat ${inp} | grep -v "\#" | awk '{print NF}' | sort | uniq -c | awk '{print $2}')
Nrs=$(${TABIX} ${inp} -R ${tgt} | grep -c "rs")
NVar=$(${TABIX} ${inp} -R ${tgt} | grep -c "MQ")


# Summarise all
GQ20=$(${TABIX} ${inp} -R ${tgt} | cut -f 10 | cut -d \: -f 4 | sort -n | awk '$1 > 20 {print}' | wc -l)
GQ60=$(${TABIX} ${inp} -R ${tgt} | cut -f 10 | cut -d \: -f 4 | sort -n | awk '$1 > 60 {print}' | wc -l)
GQ90=$(${TABIX} ${inp} -R ${tgt} | cut -f 10 | cut -d \: -f 4 | sort -n | awk '$1 > 90 {print}' | wc -l)
genomeSummary=${GQ20},${GQ60},${GQ90}


# Summarise variants
GQ20=$(${TABIX} ${inp} -R ${tgt} | grep "MQ" | cut -f 10 | cut -d \: -f 4 | sort -n | awk '$1 > 20 {print}' | wc -l)
GQ60=$(${TABIX} ${inp} -R ${tgt} | grep "MQ" | cut -f 10 | cut -d \: -f 4 | sort -n | awk '$1 > 60 {print}' | wc -l)
GQ90=$(${TABIX} ${inp} -R ${tgt} | grep "MQ" | cut -f 10 | cut -d \: -f 4 | sort -n | awk '$1 > 90 {print}' | wc -l)
variantSummary=${GQ20},${GQ60},${GQ90}


# Create table
echo -e "IID\\tAccession\\tgVCF\\tDisk_Usage\\tWidth\\tLength\\tN_Variants\\tN_dbSNP_Calls\\tGenome_GQ_Summary(GT_20,GT_60,GT_90)\\tVariant_GQ_Summary(GT_20,GT_60,GT_90)" > ${base}_checks.tsv
echo -e "${iid}\\t${acc}\\t${base}\\t${size}\\t${width}\\t${length}\\t${NVar}\\t${Nrs}\\t${genomeSummary}\\t${variantSummary}" >> ${base}_checks.tsv
