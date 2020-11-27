#!/bin/bash


# Set needed vars & directories
. ${TMPDIR}/start.sh
SM=$1
wrk=${TMPDIR}/${SM}
mkdir -p ${wrk}
cd ${wrk}


# Mount data
fusera mount -t ${key} -a ${SM} ${wrk}/${SM} > ${SM}.mount.log 2>&1 &
sleep 2m


# Exit if not mounted
if [ `ls ${wrk}/${SM}/*cram | wc -l` -eq 0 ]
then
	echo -e "\\nExiting, error mounting ${SM}\\n"
	exit
fi


# Call autosome & sex chromosomes
cram=$(ls ${wrk}/${SM}/*cram)
for chrom in chr{1..22} chr{X..Y}
	do

	# Extract chromosome
	echo -e "\\nExtracting genome to bam file\\n"
	mkdir -p ${wrk}/${chrom}
	cd ${wrk}/${chrom}
	/usr/bin/time ${SAMTOOLS} view -@ 8 -h ${cram} -T ${ref} -b ${chrom} > ${SM}.WGS.bam
	/usr/bin/time ${SAMTOOLS} index -@ 8 ${SM}.WGS.bam


	# Run haplotype caller
	echo -e "\\nPerforming WGS Calling\\n"
	/usr/bin/time java -Djava.io.tmpdir=${wrk} -Xmx12G -jar ${gatk4} HaplotypeCaller -R ${ref} --dbsnp ${dbSNP} -I ${SM}.WGS.bam -O ${SM}.${chrom}.g.vcf.gz -ERC GVCF --native-pair-hmm-threads 8 &>> ${SM}-${chrom}.vcf.log
	rm -f ${SM}.WGS.bam ${SM}.WGS.bam.bai


	# Check data
	echo -e "\\nCheck data\\n"
	/usr/bin/time md5sum ${chrom}/${SM}.${chrom}.g.vcf.gz* > ${chrom}/${SM}.${chrom}.g.vcf.gz.md5sum
	/usr/bin/time bash ${TMPDIR}/gVCF_Check.sh ${chrom}/${SM}.${chrom}.g.vcf.gz


	# Upload data
	echo -e "\\nCheck complete\\nUploading Data\\n"
	aws s3 --quiet ${wrk}/${chrom}/${SM}.${chrom}.g.vcf.gz ${s3_gvcf}/${SM}/${chrom}/${SM}.${chrom}.g.vcf.gz
	aws s3 --quiet ${wrk}/${chrom}/${SM}-${chrom}.vcf.log ${s3_gvcf}/${SM}/${chrom}/${SM}-${chrom}.vcf.log
	aws s3 --quiet ${wrk}/${chrom}/${SM}.${chrom}.g.vcf.gz.tbi ${s3_gvcf}/${SM}/${chrom}/${SM}.${chrom}.g.vcf.gz.tbi
	aws s3 --quiet ${wrk}/${chrom}/${SM}.${chrom}.g.vcf.gz_checks.tsv ${s3_gvcf}/${SM}/${chrom}/${SM}.${chrom}.tsv


	# Check upload
	echo -e "\\nUpload complete\\nChecking upload\\n"
	aws s3 ls ${s3_gvcf}/${SM}/${chrom} --summarize --human-readable


	# Clear temp dir
	echo -e "\\nChecking complete\\nProcessing complete for:   ${SM}-${chrom}\\n"
	cd ${wrk}
	rm -fr ${chrom}*

done


# Dismount & clear data
echo -e "\\n\\nProcessing complete for:\\t${SM}\\n"
cd $TMPDIR
fusera unmount ${wrk}/${SM}
rm -fr ${SM}
