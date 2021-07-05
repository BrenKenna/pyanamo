#!/bin/bash


# Parse args
# . ${PIPELINE}/job-conf.sh
SM=$1
locis=$2
wrk=${wrk}/${SM}
mkdir -p ${wrk} && cd ${wrk}
# date | awk '{print "PyAnamo:\t"$0}'
sleep $(($RANDOM % 12))s
# date | awk '{print "PyAnamo:\t"$0}'


# Check input + job-conf variable assignments
if [ -z ${SM} ] || [ -z ${locis} ] || [ -z ${project} ] || [ -z ${kg_s3} ]
then
	echo -e "PyAnamo:\\tError, exiting key ETL variables were not assigned\\n"
	echo -e "SM = ${SM} :: Loci ${locis} :: kg s3 = ${kg_s3} :: project S3 = ${project}\\n"
	cd .. && rm -fr ${SM}
	exit
fi  


# Check ETL specific software & data exists
if [ ! -f ${ref} ] || [ ! -f ${gatk4} ] || [ ! -f ${tgt} ]
then
	echo -e "PyAnamo:\\tError, exiting key reference does not exist\\n"
	echo -e "Ref = ${ref} :: GATK-4 = ${gatk4} :: VCF-Summary-Loci = ${tgt}\\n"
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


# Wait for main download to finish
# ls -lh -lha ${wrk}/*cram* | awk '{print "PyAnamo:\t"$0}'
if [ ! -z `ls -lha ${wrk}/*cram* | awk 'NR == 1 { print $1 }'` ]
then
	# echo -e "PyAnamo:\\tWaiting for active download to complete"
	while [ ! -f ${wrk}/${SM}.cram.crai ]
		do
		sleep 2m
	done

else

	# Download data
	# echo -e "PyAnamo:\\tDownloading CRAM"
	cram=$(aws s3 ls ${kg_s3}/${SM}/ | grep "am" | grep -ve "crai" | awk '{print $NF}')
	aws s3 cp --quiet ${kg_s3}/${SM}/${cram} ${wrk}/${SM}.cram
	aws s3 cp --quiet ${kg_s3}/${SM}/${cram}.crai ${wrk}/${SM}.cram.crai

fi


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


	# Exit if extraction failed
	if [ `samtools view -T ${ref} ${SM}.${chrom}.cram ${chrom} | head | wc -l` -lt 10 ]
	then
		echo -e "PyAnamo:\\tExiting, error extracting ${chrom} from ${SM}\\n"
		# cd .. && rm -fr ${chrom}
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
	bash ${PIPELINE}/gVCF_Check.sh ${SM}.${lociOut}.g.vcf.gz ${lociOut}
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
if [ -z `ls | grep "chr"` ]
then
	cd .. && rm -fr ${SM}
fi
