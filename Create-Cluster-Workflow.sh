#!/bin/bash


# Set workflow parameters for cluster
Njobs=10 # $1
Workflow=HaplotypeCaller # $2
Ntasks=200 # queried from dynamo


# Exit if key variables are not defined
if [ -z "${Njobs}" ] || [ -z "${Workflow}" ]
then
	echo -e "\\nExiting, check inputs\\n"
	exit

else
	echo -e "\\nSubmitting a cluster of ${Njobs} or ${Workflow}"
fi


# Cap jobs to not exceed the number of tasks
if [ `echo "${Njobs} / ${Ntasks}" | bc` -gt 1 ]
then
	Njobs=$((${Njobs} / 3))
fi


# Run instance with user data
aws ec2 run-instances --count ${Njobs} --user-data file://~/custom-pipeline/EC2-Fetch-Run.sh --launch-template "LaunchTemplateName=${Workflow}" > instance-data-${Njobs}.txt


# Kill instances
instanceIDs=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=${Worfklow}" --query 'Reservations[*].Instances[*].{Instance:InstanceId}' | grep "Instance" | cut -d \" -f 4 | xargs)
aws ec2 terminate-instances --instance-ids ${instanceIDs} > terminationLog.txt
