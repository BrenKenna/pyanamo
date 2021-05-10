# PyAnamo


## Running PyAnamo in AWS-Batch jobs
Follows AWS-Batch "Simple Fetch and Run" tutorial https://aws.amazon.com/blogs/compute/creating-a-simple-fetch-and-run-aws-batch-job/



## Setup Docker
Follows AWS-Batch "Simple Fetch and Run" tutorial

```
# Create ECR repository
PYANAMO=Path/To/Where/This/Folder/Was/Installed
DOCKER_INFO=GET_FROM_ECR
DOCKER_NAME=My_Super_Fun_Happy_Docker
cd ${PYANAMO}/pyanamo

sudo service docker start
sudo usermod -a -G docker ec2-user
pass=$(aws ecr get-login-password --region us-east-1)

sudo docker login --username AWS -p ${pass} ${DOCKER_INFO}
sudo docker build -t ${DOCKER_NAME} .
sudo docker tag ${DOCKER_NAME}:latest ${DOCKER_INFO}
sudo docker push ${DOCKER_INFO}


```


## Setup Tasks


```
# Create table		<= Add to client
export PYANAMO=Path/to/where/git/was/downloaded
export PYANAMO_TABLE="Testing"
cd ${PYANAMO}
aws dynamodb create-table \
	--table-name "${PYANAMO_TABLE}" \
	--attribute-definitions AttributeName=itemID,AttributeType=N AttributeName=ItemState,AttributeType=S AttributeName=taskID,AttributeType=S AttributeName=InstanceID,AttributeType=S AttributeName=Log_Length,AttributeType=N \
	--key-schema AttributeName=itemID,KeyType=HASH \
	--provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10 \
	--global-secondary-indexes file://${PYANAMO}/workflow-gsi-index.json


# Create some test tasks
for i in {1..16}
	do
	echo -e "Task-${i}|${PYANAMO_TABLE}|seq|${i},2,3"
done > ${PYANAMO_TABLE}-import.txt


# Import each of the 16 items as nested tasks: seq ${i}, seq 1, seq 2, seq 3
python import-items-generic.py -t ${PYANAMO_TABLE} -d ${PYANAMO_TABLE}-import.txt -s "|" -n ','

```


## Submit jobs


```

# Submit test array: 	Trying 2 parallel PyAnamo with HaplotypeCaller (403+246, 504+43)
arrayIDs=my-job-arrayIDs.txt
aws batch submit-job --job-name "${PYANAMO_TABLE}" --job-queue "my_pyanamo_job_queue" --job-definition "my_job_def_arn" --retry-strategy "attempts=3" --timeout "attemptDurationSeconds=345600" --array-properties "size=2" > ${arrayIDs}


# Submit full whack
arrayIDs=my-job-arrayIDs.txt
rm -f ${arrayIDs} && touch ${arrayIDs}
for i in {1..2}
	do
	aws batch submit-job --job-name "${PYANAMO_TABLE}" --job-queue "my_pyanamo_job_queue" --job-definition "my_job_def_arn" --retry-strategy "attempts=3" --timeout "attemptDurationSeconds=345600" --array-properties "size=100" >> ${arrayIDs}
	sleep 1m
done


# Summarize job array states
arrayIDs=my-job-arrayIDs.txt
for jobID in $(grep "jobId" ${arrayIDs} | cut -d \" -f 4)
	do

	# Describe the states of all jobs in the queried array
	aws batch describe-jobs --jobs "${jobID}" | grep -e "RUNNABLE" -e "SUCCEEDED" -e "SUBMITTED" -e "RUNNING" -e "FAILED" -e "RUNNING" -e "STARTING" -e "PENDING" | awk 'NR >= 2' | xargs | sed -e "s/^/${jobID}, /g" -e 's/,$//g'

done

```


## Monitor tasks on DynamoDB

```

# Tracking: Output = Total, Todo, Locked, Done
python monitor-tasks.py "${PYANAMO_TABLE}" "${N_ITERATIONS_TO_MONITOR}" "${TIME_BETWEEN_ITERATIONS}"

```

