# What is stuff doing?
The purpose of this README is to provide an *overview* of some of the key features that are *'under the hood'* in the *'Example Free Tier'* code. 


## Cluster level
With all the required debugged software + key reference datasets *'baked'* into the AMI, and launch templates for each cluster. One can just simply start an **EC2 Spot Instance Cluster** to run a script which queries itself to find out which pipeline to run :)

```bash
# Set cluster parameters
Njobs=10
Ntasks=200


# Start each cluster
for Workflow in $(echo -e "HaplotypeCaller SomeRandomThing SomethingElse")
	do

	# Cap jobs to not exceed the number of tasks
	if [ `echo "${Njobs} / ${Ntasks}" | bc` -gt 1 ]
	then
		Njobs=$((${Njobs} / 3))
	fi

	# Run instance with user data
	aws ec2 run-instances --count ${Njobs} --user-data file://~/custom-pipeline/EC2-Fetch-Run.sh --launch-template "LaunchTemplateName=${Workflow}" > ${Workflow}-instances-${Njobs}jobs.txt

done


# Kill all instances from all clusters
for Workflow in $(echo -e "HaplotypeCaller SomeRandomThing SomethingElse")
	do

	# Query instanceIDs
	instanceIDs=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=${Worfklow}" --query 'Reservations[*].Instances[*].{Instance:InstanceId}' | grep "Instance" | cut -d \" -f 4 | xargs)

	# Kill instances
	aws ec2 terminate-instances --instance-ids ${instanceIDs} > ${Workflow}-terminated-instances.txt
done
```


## User Data Script Level

### Exiting on fatal errors which will prevent pipeline from doing its job
Code snippet of some sanity checks, that if ever fail terminate the *'active'* instance. So as to avoid needlessly wasting hours / money. With an overall attitude of looking for reasons to not run the application, one can be confident that when things are running in *'full swing'*, things are being productive.... Depending on what one adds of course ;)

```bash
# Terminate if S3 Permissions are not verified (Public & Private)
if [ `aws s3 ls s3://1000genomes/1000G_2504_high_coverage/data/ERR3239277/ --summarize --human-readable | grep -c "am"` -eq 0 ] || [ `aws s3 ls s3://${workflow}/ | wc -l` -eq 0 ]
then
	echo -e "\\nExiting, error configuring aws-cli" >> logging_${jobID}.txt
	aws s3 cp logging_${jobID}.txt s3://${workflow}/logs/logging_${jobID}.txt
	aws ec2 terminate-instances --instance-ids ${instanceID}
fi
```

### Checking pipeline specific variable are defined
Given required software and reference datasets are *'baked'* into the AMI. The *'start.sh'* can act as a config file that python application can reference, when running the *'HaplotypeCaller.sh'*. 

```bash
# Terminate if any key reference data failed their assigments: start.sh
if [ ! -f ${ref} ] || [ ! -f ${dbSNP} ] || [ ! -f ${key} ] || [ ! -f ${gatk4} ]
then
	echo -e "\\nExiting, key reference data not present\\n" >> logging_${jobID}.txt
	aws s3 cp logging_${jobID}.txt s3://${workflow}/logs/logging_${jobID}.txt
	aws ec2 terminate-instances --instance-ids ${instanceID}
fi
aws s3 cp logging_${jobID}.txt s3://${workflow}/logs/logging_${jobID}.txt
```


### Sanity check pipeline can run
Running the application as a background, opens up coding possibilties for monitoring the pipeline. Initially this can take the form of terminating the active instance, if the application is no longer running after a short time window. Useful to scenario minimize wasted CPU hrs if a mistake if ever made on creating tasks for DynamoDB, examples could be referencing an input file that does not exist, or no tasks were uploaded to DynamoDB for instance.

```bash
# Run application: 	View & instance ID
echo -e "\\n\\nExecuting pipeline\\n"
nohup python ${TMPDIR}/bin/PiCaS-General.py ${VIEW_NAME} &>> logging_${jobID}.txt &
jobID=$(lsof logging_${jobID}.txt | awk 'NR == 2 { print $2}')


# Check if application will run
sleep 10m
if [ -z `lsof ${TMPDIR}/${VIEW_NAME}.${instanceID}.txt | awk 'NR == 2 { print $1 }'` ]
then
	echo -e "\\nExiting, key reference data not present\\n" >> logging_${jobID}.txt
	aws s3 cp logging_${jobID}.txt s3://${workflow}/logs/logging_${jobID}.txt
	aws ec2 terminate-instances --instance-ids ${instanceID}
fi
```

### Additional stuff
One can also set an App Time Out code block, which monitors the application at a fixed time interval so that it is possible to terminate the instance if the application is no longer running. The code block could also be extended to write out files that PyAnamo could read, so as to open communicating between Monitoring and Execution if required.

``bash
# Check application
count=0
iter=0
while [ ${count} -lt ${AppTimeOut} ]
	do

	# Print iteration
	iter=$((${iter}+1))
	echo -e "\\n\\nMonitoring iteration:\\t${iter}\\n" >> logging_${jobID}.txt


	# Check application
	if [ -z `lsof ${TMPDIR}/${VIEW_NAME}.${instanceID}.txt | awk 'NR == 2'` ]
	then
		echo -e "\\nExiting, application not active" >> logging_${jobID}.txt
		aws s3 cp logging_${jobID}.txt s3://${workflow}/logs/logging_${jobID}.txt
		aws ec2 terminate-instances --instance-ids ${instanceID}
	fi


	# Push log to s3
	echo -e "\\nApplication still active, updating log" >> logging_${jobID}.txt
	aws s3 cp logging_${jobID}.txt s3://${workflow}/logs/logging_${jobID}.txt


	# Add to counter and wait an 1hr
	count=$((${count}+1))
	sleep 1h

done
``


# Pipeline Level
The *'attitude'* of 'Pyanamo' is to iterate over all available tasks and execute the value of *'Task Script'* key. Meaning that if any given task exits, Pyanamo moves onto to the next one. With a well debugged generic task script, it very useful that if one of the ~30k samples fails to mount, the entire cluster does not explode.

### Mounting TOPMed raw sequence data
Since no input means, no output, best starting point is to avoid slowness on mounting. 
```bash

# Mount data
fusera mount -t ${key} -a ${SM} ${wrk}/${SM} > ${SM}.mount.txt 2>&1 &
sleep 2m


# Exit if not mounted
if [ `ls ${wrk}/${SM}/*cram | wc -l` -eq 0 ]
then
	echo -e "\\nExiting, error mounting ${SM}\\n"
	exit
fi

```

### Iteratively calling the genome per sample: chr1-22, chrX-Y
Since **'Spot Interruptions'** can happen after a few hours and the HaplotypeCaller takes ~8hrs on 2 threads. We openned up the task level to run on each chromosome. Facilitating taking the rest of the genome for sample on another pipeline specific cluster later. Sanity checking the data after variant calling, opens up the possibility of concatinating / storing these sanity checks in a SQL database, which can be reviewed later for analysis. Also important is to clean up temporary data, and dismounting *'TOPMed US-East-1 S3 bucket'*.

```bash
# Call autosome & sex chromosomes
cram=$(ls ${wrk}/${SM}/*cram)
for chrom in chr{1..22} chr{X..Y}
	do

	# Extract the active chromosome
	echo -e "\\nExtracting genome to bam file\\n"
	mkdir -p ${wrk}/${chrom}
	cd ${wrk}/${chrom}
	/usr/bin/time ${SAMTOOLS} view -@ 8 -h ${cram} -T ${ref} -b ${chrom} > ${SM}.WGS.bam
	/usr/bin/time ${SAMTOOLS} index -@ 8 ${SM}.WGS.bam

	# Run haplotype caller
	echo -e "\\nPerforming WGS Calling\\n"
	/usr/bin/time java -Djava.io.tmpdir=${wrk} -Xmx12G -jar ${gatk4} HaplotypeCaller -R ${ref} --dbsnp ${dbSNP} -I ${SM}.WGS.bam -O ${SM}.${chrom}.g.vcf.gz -ERC GVCF --native-pair-hmm-threads 8 &>> ${SM}-${chrom}.vcf.txt
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
```

