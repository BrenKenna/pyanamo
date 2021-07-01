#!/bin/bash


# Set vars:     Test chroms = NEK1,SOD1
# . ${PYANAMO}/start.sh
# uploadID=$(echo $RANDOM % 1000000 + 1 | bc)
SM=$1
locis=$2
wrk=${wrk}/${SM}
kg_s3=s3://1000genomes/1000G_2504_high_coverage/data
mkdir -p ${wrk} && cd ${wrk}


# 
# Check variable assignments
# echo -e "SM = ${SM} :: Loci ${locis} :: working dir = ${wrk}"
# echo -e "ref = ${ref} :: Loci ${gatk4} :: tgt = ${tgt} :: kg_s3 = ${kg_s3}"
# exit
# 


# Exit if no input
if [ -z "${SM}" ]
then
	echo -e "PyAnamo:\\tExiting, error parsing ${SM}\\n"
	cd .. && rm -fr ${SM}
	exit
fi


#########################################
#########################################
#
# HaplotypeCaller Per Supplied Loci
#
#########################################
#########################################


# Check variable assigment
if [ ! -f ${ref} ] || [ ! -f ${gatk4} ] || [ ! -f ${tgt} ]
then
	echo -e "PyAnamo:\\tError, exiting key reference does not exist\\n"
	echo -e "Ref = ${ref} :: GATK-4 = ${gatk4} :: VCF-Summary-Loci = ${tgt}"
	cd .. && rm -fr ${SM}
	exit
fi


# Download data
cram=$(aws s3 ls ${kg_s3}/${SM}/ | grep "am" | grep -ve "crai" | awk '{print $NF}')
aws s3 cp --quiet ${kg_s3}/${SM}/${cram} ${wrk}/${SM}.cram
aws s3 cp --quiet ${kg_s3}/${SM}/${cram}.crai ${wrk}/${SM}.cram.crai


# Iteratively Extract & Call supplied locis
for loci in $(echo -e "${locis}" | sed 's/,/\n/g' | sort -R)
	do

	# Set active directory
	chrom=$(echo ${loci} | cut -d \: -f 1)
	lociOut=$(echo ${loci} | sed -e 's/:/_/g' -e 's/-/_/g')
	mkdir -p ${wrk}/${chrom} && cd ${wrk}/${chrom}

	# Extract active loci
	samtools view -h -T ${ref} ${wrk}/${SM}.cram ${chrom} -C > ${SM}.${chrom}.cram
	samtools index ${SM}.${chrom}.cram
	rm -f ${SM}.cram ${SM}.cram.crai


	# Exit if extraction failed
	if [ `samtools view -T ${ref} ${SM}.${chrom}.cram ${chrom} | head | wc -l` -lt 10 ]
	then
		echo -e "PyAnamo:\\tExiting, error extracting ${chrom} from ${SM}\\n"
		cd .. && rm -fr ${chrom}
		exit
	fi


	# Call variants
	java -Djava.io.tmpdir=${wrk}/${chrom} -jar ${gatk4} HaplotypeCaller --QUIET true -R ${ref} -I ${SM}.${chrom}.cram -O ${SM}.${lociOut}.g.vcf.gz -L ${loci} -ERC GVCF --native-pair-hmm-threads 1
	rm -f ${SM}.${chrom}.cram ${SM}.${chrom}.cram.crai


	# Exit if transformation failed
	if [ `tabix -h ${SM}.${lociOut}.g.vcf.gz ${chrom} | head | wc -l` -lt 10 ]
	then
		echo -e "PyAnamo:\\tExiting, error variant calling ${chrom} from ${SM}\\n"
		cd .. && rm -fr ${chrom}
		exit
	fi
	bash ${PYANAMO}/gVCF_Check.sh ${SM}.${lociOut}.g.vcf.gz ${lociOut}
	awk '{print "PyAnamo:\t"$0}' ${SM}.${lociOut}_checks.tsv


	# Sanity check & compress archive results
	cd ..
	tar -czf ${wrk}/${SM}.${lociOut}.tar.gz ${chrom}/
	md5sum ${wrk}/${SM}.${lociOut}.tar.gz > ${wrk}/${SM}.${lociOut}.md5sum


	# Load results to S3
	# echo -e "\\nCalling for ${chrom} over ${SM} completed\\n"
	aws s3 cp --quiet ${wrk}/${SM}.${lociOut}.tar.gz ${gvcf}/${SM}/${chrom}/${SM}.${lociOut}.tar.gz
	aws s3 cp --quiet ${wrk}/${SM}.${lociOut}.md5sum ${gvcf}/${SM}/${chrom}/${SM}.${lociOut}.md5sum
	aws s3 ls --human-readable ${gvcf}/${SM}/${chrom} | grep "${SM}.${lociOut}.tar.gz" | sed 's/ \+/\t/g' | awk '{print "PyAnamo:\t"$0"\t'${gvcf}'/'${SM}'/'${chrom}'/'${SM}'.'${lociOut}'.tar.gz"}'
	rm -fr ${chrom} ${wrk}/${SM}.${lociOut}.tar.gz ${wrk}/${SM}.${lociOut}.md5sum

done


# Clean up
echo -e "PyAnamo:\\tETL completed for ${SM}"
cd .. && rm -fr ${SM}
