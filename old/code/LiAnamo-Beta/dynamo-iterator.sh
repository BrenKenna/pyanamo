#!/bin/bash


# Parse input args
tbl=$1
if [ -z "${tbl}" ]
then
	echo -e "\\nExiting no DynamoDB Workflow Table found\\n"
	exit

else
	echo -e "\\nProceeding with the ${tbl} Workflow Table\\n"
fi


# Set task args
lockID=$(echo $RANDOM % 1000000000 + 1 | bc)
wrk=/home/ec2-user/parallel_tests/task-${lockID}
db=/home/ec2-user/aws-jobs.db
mkdir -p ${wrk}
cd ${wrk}
echo -e "\\n\\nFetching todo work for ${tbl} with lockID = ${lockID}\\n"


# Get all 'todo' IDs:   Done, ask about consumed capacity with 'Next Token'
echo { \":lockKey\": {\"S\": \"todo\"} } > ${wrk}/todo-expression-value.json
aws dynamodb query \
    --table-name ${tbl} \
    --index-name "LoggingIndex" \
    --projection-expression "tokenID, lockID, taskID, TaskScript" \
    --key-condition-expression "lockID = :lockKey" \
    --expression-attribute-values file://${wrk}/todo-expression-value.json \
> ${wrk}/data-todo.txt.txt
N=$(jq .Count ${wrk}/data-todo.txt.txt)


# Handle the available work to do
if [ -z "${N}" ] || [ "${N}" == "0" ]
then
	# Exit if none
	echo -e "\\nExiting, no todo work in ${tbl}\\n"
	exit

else
	# Otherwise proceed
	echo -e "\\nProceeding with ${N} tasks\\n"
fi


# Randomly sort list of todo, check if any can be processed
for i in $(seq ${N} | awk '{ print $1 - 1}' | sort -R )
        do

        # Set vars for potentially current task:        Done 0.5 CU
        taskScript=""
        tokenID=$(jq ".Items[${i}].tokenID.S" ${wrk}/data-todo.txt.txt | sed 's/"//g')
        echo { \"tokenID\": { \"S\": \"${tokenID}\"}} > ${wrk}/getitem-${lockID}.json
        aws dynamodb get-item --table-name "${tbl}" --key file://${wrk}/getitem-${lockID}.json > ${wrk}/${tokenID}-${lockID}.txt
        taskScript=$(jq .Item.TaskScript.S ${wrk}/${tokenID}-${lockID}.txt | sed 's/"//g')
        echo "${taskScript}" > ${wrk}/task-script-${lockID}.sh
	echo -e "\\nBegining conflict check with item = ${tokenID} on lockID = ${lockID}\\n"

        # Fetch recent state to sanity check if already locked: CU = .5 + 4
        tokenState=$(aws dynamodb get-item --table-name "${tbl}" --key file://${wrk}/getitem-${lockID}.json --attributes-to-get "lockID" | jq .Item.lockID.S | sed 's/"//g')
        if [ "${tokenState}" == "todo" ]
        then

                # Set attribute aliases
		echo -e "\\nItem still available, attempting lock procedure\\n"
                echo { \"#lock\":\"lockID\" } > ${wrk}/attribute-names-${lockID}.json
                echo { \":lockingID\":{\"S\": \"${lockID}\"} } > ${wrk}/attribute-values-${lockID}.json

                # Update lockID: CU = 4
                aws dynamodb update-item --table-name "${tbl}" --key file://${wrk}/getitem-${lockID}.json --update-expression "SET #lock = :lockingID" --expression-attribute-names file://${wrk}/attribute-names-${lockID}.json --expression-attribute-values file://${wrk}/attribute-values-${lockID}.json


        # Otherwise exit
        else
                echo -e "\\nExiting, task is already locked by another process\\n"
                continue

        fi


        # Manage Conflicts + Execution with current lockID: Get latest instead of jq
        sleep $(echo $RANDOM % 3 + 1 | bc)s
        tokenState=$(aws dynamodb get-item --table-name "${tbl}" --key file://${wrk}/getitem-${lockID}.json --attributes-to-get "lockID" | jq .Item.lockID.S | sed 's/"//g')
        if [ "${tokenState}" != "${lockID}" ]
        then

                # Exit if conflict
                echo "\\nExiting, lockIDs do not match\\n"
                continue


        # Proceed if no conflicts & taskScript is not null
        elif [ "${tokenState}" == "${lockID}" ] && [ ! -z "${taskScript}" ]
        then

                # Execute task script
                echo -e "\\nCurrent instance = ${lockID} locked task ${taskScript} for item = ${tokenID}\\n"
                bash task-script-${lockID}.sh | xargs | sed -e 's/^/"/g' -e 's/$/"/g' | awk '{ print "'${tokenID}','$(echo ${taskScript} | sed 's/ /-/g')',"$0 }' > ${wrk}/Task-${lockID}.Logging.txt

                # Update lockID & logging fields
                echo -e "\\nTask ${tokenID} complete, marking token as done\\n"
                echo { \"#lock\":\"lockID\", \"#log\":\"Log\" } > ${wrk}/attribute-names-${lockID}.json
                Logging=$(cat ${wrk}/Task-${lockID}.Logging.txt | sed "s/\"/'/g" )
                echo { \":lockingID\":{\"S\": \"done_${lockID}\"}, \":logging\":{\"S\": \"Successful log \= ${Logging}\" } } > ${wrk}/attribute-values-${lockID}.json
                aws dynamodb update-item --table-name "${tbl}" --key file://${wrk}/getitem-${lockID}.json --update-expression "SET #lock = :lockingID, #log = :logging" --expression-attribute-names file://${wrk}/attribute-names-${lockID}.json --expression-attribute-values file://${wrk}/attribute-values-${lockID}.json
                sleep $(echo $RANDOM % 4 + 1 | bc)s


        # Otherwise exit
        else
                echo -e "\\nError checking conflicts, exiting\\n"
                continue
        fi


        # Log completion
        echo -e "\\nProcessing complete for item = ${tokenID} under lockID = ${lockID}\\n"
        rm -f ${wrk}/*-${lockID}.txt ${wrk}/*-${lockID}.lson
done
