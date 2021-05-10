#!/bin/bash


# Set vars
. ${PYANAMO}/start.sh
inp=$1
wrk=${wrk}/${inp}
uploadID=$(echo $RANDOM % 1000000 + 1 | bc)
mkdir -p ${wrk}/PCA ${wrk}/raw_trace
cd ${wrk}


# Exit if no input
if [ -z "${inp}" ]
then
	echo -e "\\nExiting, error parsing ${inp}"
	cd ..
	rm -fr ${inp}
	exit
fi

#
# echo -e "${inp} ${wrk}\\n${LASER} ${PYANAMO} ${kg_data}"
# which bgzip bcftools tabix Rscript
#


#########################################
#########################################
# 
# EXTRACTION
# 
#########################################
#########################################


# Download reference data + TRACE: Errors on below variables are caught laterz
# echo -e "\\nDownloading required reference data + software\\n"
aws s3 --quiet cp ${kg_data} ${wrk}/1KG-TRACE/
aws s3 --quiet cp ${LASER} ${wrk}/
aws s3 --quiet cp ${key} ${wrk}/
LASER=${wrk}/LASER-2.04
kg_data=${wrk}/1KG-TRACE
key=${wrk}/prj_16444.ngc
kgLoci=${wrk}/tgt.bed


# Verify reference data integrity
if [ "${kg_dataMD5}" != $(md5sum ${wrk}/1KG-TRACE/GRCh38-1KG-Ancestry.tar.gz | awk '{print $1}') ] || [ "${laserMD5}" != $(md5sum ${wrk}/LASER-2.04.tar.gz | awk '{print $1}') ]
then

	# Exit on corrupted transfers
	echo -e "\\nExiting, LASER or 1KG-TRACE data failed to download\\n"
	cd ..
	rm -fr ${inp}
	exit

else

	# Otherwise proceed
	# echo -e "\\nLASER & 1KG-TRACE download verified, unpacking data\\n"
	tar -xf ${wrk}/LASER-2.04.tar.gz
	tar -xf ${wrk}/1KG-TRACE/GRCh38-1KG-Ancestry.tar.gz
	# which ${LASER}/trace ${LASER}/vcf2geno/vcf2geno
	rm -f ${wrk}/LASER-2.04.tar.gz ${wrk}/1KG-TRACE/GRCh38-1KG-Ancestry.tar.gz

fi


# Download VCF via Pre-Signed URLs
# echo -e "\\nDownloading Input VCF\\n"
vcf=$(curl -sX POST -F ngc="@${key}" "https://www.ncbi.nlm.nih.gov/Traces/sdl/1/retrieve?acc=${inp}&location=s3.us-east-1" | grep "vcf" | grep -ve "tbi" -ve "csi" | grep "link" | cut -d \: -f 2- | sed -e 's/,$//g' -e 's/^ //g' -e 's/https:\/\//https:\/\/\//g' -e "s/\"//g")
# vcfIndex=$(curl -sX POST -F ngc="@${key}" "https://www.ncbi.nlm.nih.gov/Traces/sdl/1/retrieve?acc=${inp}&location=s3.us-east-1" | grep "vcf" | grep -e "tbi" -e "csi" | grep "link" | cut -d \: -f 2- | sed -e 's/,$//g' -e 's/^ //g' -e 's/https:\/\//https:\/\/\//g' -e "s/\"//g")
curl -s -o ${wrk}/raw_trace/${inp}.vcf.gz "${vcf}"
tabix -p vcf -f ${wrk}/raw_trace/${inp}.vcf.gz


# Query PCA loci
# echo -e "\\nDownload complete, extracting PCA loci\\n"
tabix ${wrk}/raw_trace/${inp}.vcf.gz -h -B ${kgLoci} | bgzip -c > ${wrk}/raw_trace/tmp
mv ${wrk}/raw_trace/tmp ${wrk}/raw_trace/${inp}.vcf.gz
tabix -p vcf -f ${wrk}/raw_trace/${inp}.vcf.gz


# Exit if subsetting failed
if [ ! -f ${wrk}/raw_trace/${inp}.vcf.gz ] || [ `tabix ${wrk}/raw_trace/${inp}.vcf.gz chr21 | head | wc -l` -lt 10 ]
then
	echo -e "\\nExiting, extraction failed for ${inp}"
	cd ..
	rm -fr ${inp}
	exit
fi


# Convert VCF to GENO format
# echo -e "\\nExtraction complete, converting to GENO format for PCA\\n"
${LASER}/vcf2geno/vcf2geno --inVcf ${wrk}/raw_trace/${inp}.vcf.gz --out ${wrk}/PCA/${inp}-TRACE-PCA &>> ${wrk}/${inp}-TRACE-Vcf2Geno.log
sed 's/^chr//g' ${wrk}/PCA/${inp}-TRACE-PCA.site > tmp
mv tmp ${wrk}/PCA/${inp}-TRACE-PCA.site
rm -fr raw_trace/


# Exit if vcf2geno conversion failed
if [ ! -f ${wrk}/PCA/${inp}-TRACE-PCA.geno ]
then
	echo -e "\\nExiting, vcf2geno conversion failed"
	cd ..
	rm -fr ${inp}
	exit
fi


#########################################
#########################################
# 
# TRANSFORMATION
# 
#########################################
#########################################


# Perform PCA
# echo -e "\\nConversion complete, performing PCA\\n"
ref_site=${wrk}/1KG-GRCh38-ALL-CommonQC.site
ref_geno=${wrk}/1KG-GRCh38-ALL-CommonQC.geno
ref_coord=${wrk}/1KG-GRCh38-ALL-CommonQC.RefPC.coord
${LASER}/trace -s ${wrk}/PCA/${inp}-TRACE-PCA.geno -c ${ref_coord} -g ${ref_geno} -o ${wrk}/${inp}-TRACE-PCA -k 4 -nt 1 &>> ${wrk}/${inp}-TRACE-PCA.log
rm -fr PCA/


# Exit if PCA failed
if [ ! -f ${wrk}/${inp}-TRACE-PCA.ProPC.coord ]
then
	echo -e "\\nExiting, PCA failed"
	cd ..
	rm -fr ${inp}
	exit
fi


# Classify ancestry
# echo -e "\\nPCA complete, classifying ancestry\\n\\n"
# cat ${wrk}/${inp}-TRACE-PCA.ProPC.coord
cut -f 1,7- ${wrk}/${inp}-TRACE-PCA.ProPC.coord > ${wrk}/${inp}-TracePCA.txt
Rscript --no-save --no-restore ${PYANAMO}/classify-ancestry-trace.r ${wrk}/${inp}-TracePCA.txt ${PYANAMO}/kg-trace-eu-rf-model.rds ${wrk}/${inp}-TracePCA-Ancestry.txt &>> ${wrk}/${inp}-Classify.log


# Log results to DynamoDB with an easy to parse value in log key
# echo -e "\\nClassification complete, logging results\\n\\n"
awk '{print "Ancestry-Results:\t"$0}' ${inp}-TracePCA-Ancestry.txt


#########################################
#########################################
# 
# LOADING
# 
#########################################
#########################################


# Upload data
# echo -e "\\n\\nProcess complete, pushing results to S3\\n"
for i in $(ls ${wrk}/*log ${wrk}/*coord ${wrk}/*txt | grep -ve "KG")
	do
	base=$(basename ${i})
	aws s3 --quiet cp ${i} ${ancestry}/${inp}/${uploadID}_${base}
done


# Clear data
echo -e "\\nETL Complete for ${inp}\\n"
cd ..
rm -fr ${inp}
