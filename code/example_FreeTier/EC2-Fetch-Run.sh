#!/bin/bash


# Install aws-client for command line access
echo -e "\\n\\nInstalling Software\\n\\n\\n" >> logging_${jobID}.txt
sudo yum update -y &>> logging_${jobID}.txt
sudo pip install awscli --user --upgrade &>> logging_${jobID}.txt
export instanceID=$(ec2-metadata -i | cut -d \: -f 2)


# Set vars
export TMPDIR=/tmp/pipeline
source ${TMPDIR}/start.sh
export VIEW_NAME=MyTestWorkflow 	# Fetch from ec2-metadata
export AppTimeOut=72
export host=$(hostname)
export CMAKE_PREFIX_PATH="${TMPDIR}/software"
export PATH=${TMPDIR}/software/bin:$PATH 
export PYTHONPATH=${TMPDIR}/
jobID=$(echo $RANDOM % 100000 + 1 | bc)


# 
# Define key pipeline data
# export ref=${TMPDIR}/Reference/hs38DH.fa
# export dbSNP=${TMPDIR}/Reference/dbsnp_146.hg38.vcf.gz
# export key=${TMPDIR}/Reference/prj_16444.ngc
# export gatk4=${TMPDIR}/Reference/gatk-package-4.1.4.0-local.jar
#


# Setup working directory
wrk=${TMPDIR}/${VIEW_NAME}
mkdir -p ${wrk}
cd ${wrk}

echo -e "##################################################" > logging_${jobID}.txt
echo -e "##################################################" >> logging_${jobID}.txt
echo -e "\\n\\nInitiating Logging for Task:\\t${VIEW_NAME}" >> logging_${jobID}.txt
echo -e "\\n\\nTask Timeout:\\t${AppTimeOut}" >> logging_${jobID}.txt
echo -e "\\n\\nInstance ID:\\t${instanceID}" >> logging_${jobID}.txt
echo -e "##################################################" >> logging_${jobID}.txt
echo -e "##################################################" >> logging_${jobID}.txt
aws s3 cp logging_${jobID}.txt s3://${workflow}/logs/logging_${jobID}.txt


# 
# Old code before install everything on AMI + Avoid need to download reference datasets
#
# Install miniconda
# echo -e "\\n\\n\\nInstalling Miniconda and Application Based Software\\n\\n" &>> logging_${jobID}.txt
# wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh &>> logging_${jobID}.txt 
# chmod +x Miniconda3-latest-Linux-x86_64.sh &>> logging_${jobID}.txt 
# ./Miniconda3-latest-Linux-x86_64.sh -b -p ${TMPDIR}/software &>> logging_${jobID}.txt
# aws s3 cp logging_${jobID}.txt s3://${workflow}/logs/logging_${jobID}.txt
#
# Install PiCaS-Generic.py Dependencies: 	gfal2, picas and couchDB
# conda install -y -c conda-forge python-gfal2 &>> logging_${jobID}.txt
# sudo pip install picas couchdb couchdblogger &>> logging_${jobID}.txt
# aws s3 cp logging_${jobID}.txt s3://${workflow}/logs/logging_${jobID}.txt
#
# Fetch the pipeline + reference data archive
# aws s3 cp ${s3_pipeline} ${TMPDIR}/pipeline.tar.gz &>> logging_${jobID}.txt
# tar -xvf pipeline.tar.gz &>> logging_${jobID}.txt
# aws s3 cp logging_${jobID}.txt s3://${workflow}/logs/logging_${jobID}.txt
#


#################################################
#################################################

# Verify Pipeline Variable + Execution

#################################################
#################################################


# Terminate if S3 Permissions are not verified (Public & Private)
if [ `aws s3 ls s3://1000genomes/1000G_2504_high_coverage/data/ERR3239277/ --summarize --human-readable | grep -c "am"` -eq 0 ] || [ `aws s3 ls s3://${workflow}/ | wc -l` -eq 0 ]
then
	echo -e "\\nExiting, error configuring aws-cli" >> logging_${jobID}.txt
	aws s3 cp logging_${jobID}.txt s3://${workflow}/logs/logging_${jobID}.txt
	aws ec2 terminate-instances --instance-ids ${instanceID}
fi


# Terminate if any key reference data failed their assigments: start.sh
if [ ! -f ${ref} ] || [ ! -f ${dbSNP} ] || [ ! -f ${key} ] || [ ! -f ${gatk4} ]
then
	echo -e "\\nExiting, key reference data not present\\n" >> logging_${jobID}.txt
	aws s3 cp logging_${jobID}.txt s3://${workflow}/logs/logging_${jobID}.txt
	aws ec2 terminate-instances --instance-ids ${instanceID}
fi
aws s3 cp logging_${jobID}.txt s3://${workflow}/logs/logging_${jobID}.txt



#################################################
#################################################

# Run the Application

#################################################
#################################################


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


####################################################
####################################################

# Monitor Application On Verification Success

####################################################
####################################################


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


	# Add to counter and wait 4hrs: 	Switch to 15-30 mins ?
	count=$((${count}+1))
	sleep 1h

done


# Force instance suicide if monitoring stops
echo -e "\\n\\nExiting quirk with while loop" &>> logging_${jobID}.txt
aws s3 cp logging_${jobID}.txt s3://${workflow}/logs/logging_${jobID}.txt
aws ec2 terminate-instances --instance-ids ${instanceID}
