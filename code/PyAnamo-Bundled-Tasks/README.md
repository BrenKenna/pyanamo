# PyAnamo: Bundling Tasks
Updated the Workflow Schema to facilitate placing multiple Task Scripts into an item. The Task Script Key is now a dictionary, where each item inside of it carries the script to run and a status of that script. The Log and Log_Lengths were also updated and whose updates are appended to DynanmoDB. The Done_Date is now only updated once all sub-tasks have been processed.


ToDo:

**i). Add querying functions to summarize table states.**

**ii). Function to reset the lockID of a list of itemIDs / query.**

**iii). Change the Log_Length value to a dictionary instead of a list.**

**iv). Add EC2-InstanceID to schema.**

**v). Add in some more error handling.**

**vi). Change Log_Length to Log_Summary and add in a CPU-Time key?**


## Creating and Populating the Test Table
The conversion to Python saw some schema changes where the **Log Key** is now a json string, and the addition of *"Done_Date"*, *"Locked_Date"* and *"Log_Length keys"*. The aws client is still used to create the table, because for some unknown reason boto3 could not return any items on query when it was used to create the table.

**i). itemID = Unique ID to identify an item on DynamoDB.**

**ii). taskID = An ID which relates the itemID to the TaskScript, ex SampleIDs.**

**iii). lockID = ID to manage conflicts with 3 possible values; todo, locked, done.**

**iv). Log = Output from executing the TaskScript value.**

**v). TaskScript = What PyAnamo will exeucte if the itemID is still available.**

**vii). Done & Lock Date = Separate keys whose values is the date when the item was locked and completed.**

**viii). Log_Length = Length of the log file.**


```bash
# Set vars
wrk=/home/ec2-user
db=${wrk}/aws-jobs.db
tbl="tbl="HaplotypeCaller_Bundled"
mkdir -p ${wrk}/parallel_tests


# Create table
aws dynamodb create-table \
    --table-name "${tbl}" \
    --attribute-definitions AttributeName=itemID,AttributeType=S AttributeName=taskID,AttributeType=S AttributeName=Log_Length,AttributeType=S AttributeName=TaskScript,AttributeType=S AttributeName=ID_Index,AttributeType=S AttributeName=lockID,AttributeType=S AttributeName=Log,AttributeType=S AttributeName=Lock_Date,AttributeType=S AttributeName=Done_Date,AttributeType=S \
    --key-schema AttributeName=itemID,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10 \
    --global-secondary-indexes file://${wrk}/workflow-gsi-index-2.json


# Import tasks: The final argument is to communicate whether to bundle tasks
sleep 1m
data=${wrk}/dynamo-import.txt
python import-items.py "${tbl}" "${data}" 1
```


## Testing Principal with 3 Parallel Aplication Instances

### Setup and Execute the Parallel Applications
Not evaluated past exectution, since these tests were performed previously.


**1. Can query the todo items.**

**2. Can execute the task script.**

**3. Can detect items already locked by another application (ie Raise Conflicts Errors).**

**4. None of the 3 applications will execute the active TaskScript Keys value after raising a conflict error.**


```bash
# Test parallel execution
echo -e "cd /home/ec2-user" > ${wrk}/PyAnamo-Bundled-Parallel-Test.txt
for i in {1..3}
	do
	echo -e "python pyanamo-beta-bundled.py ${tbl} > ${wrk}/bundled-thread-${i}.txt"
done >> ${wrk}/PyAnamo-Bundled-Test.txt


# Execute test with 3 staggered parallel instances
parallel -j 3 < ${wrk}/PyAnamo-Bundled-Test.txt


# Archive results
tar -czf PyAnamo-Bundled.tar.gz *undled* *py
```
