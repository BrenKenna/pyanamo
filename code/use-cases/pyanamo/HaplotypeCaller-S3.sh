#!/bin/bash


# Set vars:     Test chroms = NEK1,SOD1
# . ${PYANAMO}/start.sh
# uploadID=$(echo $RANDOM % 1000000 + 1 | bc)
SM=$1
chroms=$2
wrk=${wrk}/${SM}
mkdir -p ${wrk} && cd ${wrk}


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


# Iteratively Extract & Call supplied locis
for chrom in $(echo -e "${chroms}" | sed 's/,/\n/g' | sort -R)
	do

	# Extract active loci
	mkdir -p ${wrk}/${chrom} && cd ${wrk}/${chrom}
	aws s3 --quiet cp ${bam}/${SM}/${chrom}/${SM}.cram ./${SM}.${chrom}.cram
	aws s3 --quiet cp ${bam}/${SM}/${chrom}/${SM}.cram.crai ./${SM}.${chrom}.cram.crai
	touch ${SM}.${chrom}.cram.crai


	# Exit if extraction failed
	if [ `samtools view -T ${ref} ${SM}.${chrom}.cram ${chrom} | head | wc -l` -lt 10 ]
	then
		echo -e "PyAnamo:\\tExiting, error extracting ${chrom} from ${SM}\\n"
		cd .. && rm -fr ${SM}
		exit
	fi


	# Call variants
	java -Djava.io.tmpdir=${wrk}/${chrom} -jar ${gatk4} HaplotypeCaller --QUIET true -R ${ref} -I ${SM}.${chrom}.cram -O ${SM}.${chrom}.g.vcf.gz -L ${chrom} -ERC GVCF --native-pair-hmm-threads 2
	rm -f ${SM}.${chrom}.cram ${SM}.${chrom}.cram.crai


	# Exit if transformation failed
	if [ `tabix -h ${SM}.${chrom}.g.vcf.gz ${chrom} | head | wc -l` -lt 10 ]
	then
		echo -e "PyAnamo:\\tExiting, error variant calling ${chrom} from ${SM}\\n"
		cd .. && rm -fr ${SM}
		exit
	fi
	bash ${PYANAMO}/gVCF_Check-2.sh ${SM}.${chrom}.g.vcf.gz ${chrom}
	awk '{print "PyAnamo:\t"$0}' ${SM}.${chrom}_checks.tsv


	# Sanity check & compress archive results
	cd ..
	tar -czf ${wrk}/${SM}.${chrom}.tar.gz ${chrom}/
	md5sum ${wrk}/${SM}.${chrom}.tar.gz > ${wrk}/${SM}.${chrom}.md5sum


	# Load results to S3
	# echo -e "\\nCalling for ${chrom} over ${SM} completed\\n"
	aws s3 cp --quiet ${wrk}/${SM}.${chrom}.tar.gz ${gvcf}/${SM}/${SM}.${chrom}.tar.gz
	aws s3 cp --quiet ${wrk}/${SM}.${chrom}.md5sum ${gvcf}/${SM}/${SM}.${chrom}.md5sum
	aws s3 ls --human-readable ${gvcf}/${SM}/ | grep "${SM}.${chrom}.tar.gz" | sed 's/ \+/\t/g' | awk '{print "PyAnamo:\t"$0"\t'${gvcf}'/'${SM}'/'${SM}'.'${chrom}'.tar.gz"}'
	rm -fr ${chrom}

done


# Clean up
# echo -e "PyAnamo:\\tETL completed for ${SM}"
cd .. && rm -fr ${SM}
