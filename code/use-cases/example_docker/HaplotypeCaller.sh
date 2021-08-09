#!/bin/bash


# Set vars:     chroms = NEK1,SOD1
# . ${PYANAMO}/start.sh
SM=$1
chroms=$2
wrk=${wrk}/${SM}
# uploadID=$(echo $RANDOM % 1000000 + 1 | bc)
mkdir -p ${wrk} ${wrk}/Reference
cd ${wrk}


# Exit if no input
if [ -z "${SM}" ]
then
	echo -e "PyAnamo:\\tExiting, error parsing ${SM}\\n"
	cd ..
	rm -fr ${SM}
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
if [ ! -f ${ref} ] || [ ! -f ${key} ] || [ ! -f ${gatk4} ] || [ ! -f ${tgt} ]
then
	echo -e "PyAnamo:\\tError, exiting key reference does not exist\\n"
	echo -e "Ref = ${ref} :: Key = ${key} :: GATK-4 = ${gatk4} :: VCF-Summary-Loci = ${tgt}"
	exit
fi


# Iteratively Extract & Call supplied locis
for chrom in $(echo -e "${chroms}" | sed 's/,/\n/g' | sort -R)
do

	# Extract active loci
	mkdir -p ${wrk}/${chrom} && cd ${wrk}/${chrom}
	cram=$(curl -sX POST -F ngc="@${key}" "https://www.ncbi.nlm.nih.gov/Traces/sdl/1/retrieve?acc=${SM}&location=s3.us-east-1" | grep "cram" | grep -v "crai" | grep "link" | cut -d \: -f 2- | sed -e 's/,$//g' -e 's/^ //g' -e 's/https:\/\//https:\/\/\//g' -e "s/\"//g")
	crai=$(curl -sX POST -F ngc="@${key}" "https://www.ncbi.nlm.nih.gov/Traces/sdl/1/retrieve?acc=${SM}&location=s3.us-east-1" | grep "crai" | grep "link" | cut -d \: -f 2- | sed -e 's/,$//g' -e 's/^ //g' -e 's/https:\/\//https:\/\/\//g' -e "s/\"//g")
	samtools view -h -C -T ${ref} ${cram} -X ${crai} ${chrom} > ${SM}.${chrom}.cram
	samtools index ${SM}.${chrom}.cram


	# Exit if extraction failed
	if [ `samtools view -T ${ref} ${SM}.${chrom}.cram ${chrom} | head | wc -l` -lt 10 ]
	then
		echo -e "PyAnamo:\\tExiting, error extracting ${chrom} from ${SM}\\n"
		cd .. && rm -fr ${SM}
		exit
fi


	# Call variants & sanity check results
	java -Djava.io.tmpdir=${wrk}/${chrom} -jar ${gatk4} HaplotypeCaller --QUIET true -R ${ref} -I ${SM}.${chrom}.cram -O ${SM}.${chrom}.g.vcf.gz -L ${chrom} -ERC GVCF --native-pair-hmm-threads 1
	rm -f ${SM}.${chrom}.cram ${SM}.${chrom}.cram.crai


	# Exit if transformation failed
	if [ `tabix -h ${SM}.${chrom}.g.vcf.gz ${chrom} | head | wc -l` -lt 10 ]
	then
		echo -e "PyAnamo:\\tExiting, error variant calling ${chrom} from ${SM}\\n"
		cd .. && rm -fr ${SM}
		exit
	fi
	bash ${PIPELINE}/gVCF_Check.sh ${SM}.${chrom}.g.vcf.gz ${chrom}


	# Compress archive results
	cd ..
	tar -czf ${wrk}/${SM}.${chrom}.tar.gz ${chrom}/
	md5sum ${wrk}/${SM}.${chrom}.tar.gz > ${wrk}/${SM}.${chrom}.md5sum


	# Load results to S3
	# echo -e "\\nCalling for ${chrom} over ${SM} completed\\n"
	aws s3 cp --quiet ${wrk}/${SM}.${chrom}.tar.gz ${gvcf}/${SM}/${SM}.${chrom}.tar.gz
	aws s3 cp --quiet ${wrk}/${SM}.${chrom}.md5sum ${gvcf}/${SM}/${SM}.${chrom}.md5sum
	remoteData=$(aws s3 ls --summarize ${gvcf}/${SM}/${SM}.${chrom}.tar.gz | sed 's/ /;/g')
	awk '{print "PyAnamo:\t"$0"\t'${remoteData}'"}' ${chrom}/${SM}.${chrom}_checks.tsv | sed 's/;/\t/g'
	rm -fr ${chrom}

done


# Clean up
# echo -e "PyAnamo:\\tETL completed for ${SM}"
cd .. && rm -fr ${SM}
