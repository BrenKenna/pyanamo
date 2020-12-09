#!/bin/bash


# Parse input args
tbl=$1
deleteTable=${2:-0}
testing=${3:-0}
if [ -z "${tbl}" ]
then
	echo -e "\\nExiting no DynamoDB Workflow Table found\\n"
	exit

else
	echo -e "\\nProceeding with the ${tbl} Workflow Table\\n"
fi


# Set vars
wrk=/home/ec2-user
db=${wrk}/aws-jobs.db
mkdir -p ${wrk}
cd ${wrk}


# Clear table
if [ ${deleteTable} -eq 1 ]
then
	echo -e "\\n\\nDeleting input table ${tbl}\\n\\n"
	aws dynamodb delete-table --table-name "${tbl}"
	sleep 1m
fi


# Create table
echo -e "\\n\\nCreating input table ${tbl}\\n\\n"
aws dynamodb create-table \
    --table-name "${tbl}" \
    --attribute-definitions AttributeName=tokenID,AttributeType=S AttributeName=taskID,AttributeType=S AttributeName=WorkFlow,AttributeType=S AttributeName=TaskScript,AttributeType=S AttributeName=ID_Index,AttributeType=N AttributeName=lockID,AttributeType=S  AttributeName=Log,AttributeType=S  \
    --key-schema AttributeName=tokenID,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10 \
    --global-secondary-indexes file://${wrk}/workflow-gsi-index.json
sleep 1m


# Iteratively add items
if [ ${testing} -eq 1 ] && [ -f ${wrk}/dynamo-import.txt ]
then
	# Iteratively add 10 test items
	echo -e "\\n\\nAdding test items to input table ${tbl}\\n\\n"
	counter=0
	for i in $(cat ${wrk}/dynamo-import.txt)
		do

		# Set vars for table
		counter=$((${counter}+1))
		N=$(echo $RANDOM % 25 + 1 | bc)
		taskscript=$(echo "seq ${N}")
		taskID=$(echo -e "${i}" | cut -d \| -f 2)

		# Write token to a file
		echo -e "\\n\\nAdding test item ${counter}-VC\\n\\n"
		echo -e '{ "tokenID": {"S": "'${counter}'-VC"}, "taskID": { "S": "'${taskID}'" }, "ID_Index": {"N": "'${counter}'"}, "Workflow": {"S": "'${workflow}'"}, "TaskScript": {"S": "'${taskscript}'"}, "lockID": {"S": "todo"}, "Log": {"S": "NULL"} }' > ${wrk}/item.json

		# Add item to table
		aws dynamodb put-item --table-name "${tbl}" --return-consumed-capacity TOTAL --item file://${wrk}/item.json
		rm -f ${wrk}/item.json
		sleep 1s
	done
fi
