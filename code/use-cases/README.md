
# Running PyAnamo in AWS-Batch jobs
Follows the AWS-Batch "Simple Fetch and Run" tutorial https://aws.amazon.com/blogs/compute/creating-a-simple-fetch-and-run-aws-batch-job/

Users will also need to make the appropriate edits to the "***job-conf.sh***" to set their own required variables such as output result directories on S3, locations of their own reference data etc etc. For the sake of simplicity the jobs submitted here are only going to run the seq Linux command.



## a). Create Some Test Tasks

The "***code/import-items.py***" wrapper script creates the supplied table if it does not exist. See "***Creating and Managing Workflows.md***" on the repo landing page for any background info.


```bash
# Write a list nested items to the same table: Delimiters optional
echo -e "
itemID|TaskID|TaskScript|TaskArgs
Seq_Test_1|Seq_8_2_1|seq|8,2,1
Seq_Test_2|Seq_4_5_3|seq|4,5,3
Seq_Test_3|Seq_6_7_9|seq|6,7,9
Seq_Test_4|Seq_5_8_2|seq|5,8,2
" > import-nested-testing.txt

# Import
python import-items.py 'Testing' 'us-east-1' 'import-nested-testing.txt' '|' ','
```



## b). Submit & Summarize Job Arrays


```bash
# Stagger submit 2 job arrays composed of 100 jobs
arrayIDs=my-job-arrayIDs.txt
rm -f ${arrayIDs} && touch ${arrayIDs}
for i in {1..2}
	do
	aws batch submit-job --job-name "Testing" --job-queue "my_pyanamo_job_queue" \ 
		--job-definition "my_job_def_arn" --retry-strategy "attempts=3" \ 
		--timeout "attemptDurationSeconds=345600" \ 
		--array-properties "size=100" >> ${arrayIDs}
	sleep 1m
done

# Summarize the job array states
arrayIDs=my-job-arrayIDs.txt
for jobID in $(grep "jobId" ${arrayIDs} | cut -d \" -f 4)
	do

	# Describe the states of all jobs in the queried array
	aws batch describe-jobs --jobs "${jobID}" | grep -e "RUNNABLE" -e "SUCCEEDED" -e "SUBMITTED" -e "RUNNING" -e "FAILED" -e "RUNNING" -e "STARTING" -e "PENDING" | awk 'NR >= 2' | xargs | sed -e "s/^/${jobID}, /g" -e 's/,$//g'
done
```



## c). Monitoring Workflows

You will want to know two things for managing your workflows:

​	i). How far along am I with the tasks I setup?

​	ii). Is my workflow still active?

### i). Summarize the item states of the items & their nested tasks on DynamoDB

```python
# Import
python
import manager as pmanager

# Instantiate
table_name = 'Testing'
aws_region = 'us-east-1'
manager_client = pmanager.PyAnamo_Manager(dynamo_table = table_name, region = aws_region)
manager_client.handle_DynamoTable(table_name)

# Monitor tasks in general
manager_client.monitor_task(table_name, Niterations = 1, waitTime = 0)

# Summarize nested tasks: Counts + itemIDs of todo, 1-25%, 26-75%, 76-99%, done
manager_client.summarize_nestedTasks(table_name)
itemSummary = manager_client.summarize_nestedTasks(table_name, output_results = 1)
```

### ii). Relate AWS batch job states to their item states on DynamoDB

This is useful for checking how many locked items are no longer active because the job that had locked them has since terminated. The out is a dictionary for each AWS Batch Job state and a list of item IDS, so that you can pass the required list of item IDs to some method in the manager client such as: "***reset_itemState***" or "***delete_singleItem***"

```python
# Import
python
import manager as pmanager

# Instantiate
table_name = 'Testing'
aws_region = 'us-east-1'
manager_client = pmanager.PyAnamo_Manager(dynamo_table = table_name, region = aws_region)
manager_client.handle_DynamoTable(table_name)

# Check states
results = manager_client.getItem_JobStates(table_name)

# View count of the itemIDs per job state: 
[ str('Job State ' + resultState + ' = ' + str(len(results[resultState]))) for resultState in results.keys() ]
```
