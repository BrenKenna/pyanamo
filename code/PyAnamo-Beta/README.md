# PyAnamo-Beta
The overall principal of the LiAnamo code ported well onto python and can be used to complete **Aim-1**, which will take the form of data generation of the SOD1 gene. Additionally it will also be nice to get a sense of running at scale provisioning budget.

To Do / Open Questions:

**i). Coorindate on a *"proper" task schema. **

**ii). Coorindate on Provisioning. **

**iii). Add ec2-instance ID key.**

**iv). Is it worthwhile to query table read/write before fetching next task?**

**v). SOD1 calling tests in AWS-Batch jobs.**


## Creating and Populating the Test Table
The conversion to Python saw some schema changes where the **Log Key** is now a json string, and the addition of *"Done_Date"*, *"Locked_Date"* and *"Log_Length keys"*. The aws client is still used to create the table, because for some unknown reason boto3 could not return any items on query when it was used to create the table.

**i). itemID = Unique ID to identify an item on DynamoDB.**

**ii). taskID = An ID which relates the itemID to the TaskScript, ex SampleIDs.**

**iii). lockID = ID to manage conflicts with 3 possible values; todo, locked, done.**

**iv). Log = Output from executing the TaskScript value.**

**v). TaskScript = What LiAnamo-Beta will exeucte if the itemID is still available.**

**vii). Done & Lock Date = Separate keys whose values is the date when the item was locked and completed.**

**viii). Log_Length = Length of the log file.**


```bash
# Set vars
wrk=/home/ec2-user
db=${wrk}/aws-jobs.db
tbl="HaplotypeCaller"
mkdir -p ${wrk}/parallel_tests


# Download metadata DB
echo -e "select Run, Sample_Name, Ancestry from dbgap where Ancestry = 'EU' order by random() limit 10;" | sqlite3 ${db} > ${wrk}/dynamo-import.txt


# Create table
aws dynamodb create-table \
    --table-name "${tbl}" \
    --attribute-definitions AttributeName=itemID,AttributeType=S AttributeName=taskID,AttributeType=S AttributeName=Log_Length,AttributeType=S AttributeName=TaskScript,AttributeType=S AttributeName=ID_Index,AttributeType=S AttributeName=lockID,AttributeType=S AttributeName=Log,AttributeType=S AttributeName=Lock_Date,AttributeType=S AttributeName=Done_Date,AttributeType=S \
    --key-schema AttributeName=itemID,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10 \
    --global-secondary-indexes file://${wrk}/workflow-gsi-index-2.json

# Import the test data
sleep 1m
data=${wrk}/dynamo-import.txt
python import-items.py "${tbl}" "${data}"

```


## Testing Principal with 3 Parallel Aplication Instances

### Setup and Execute the Parallel Applications
Since the production environment will have thousands of distinct applications querying the one table, we need to be sure that the therory holds-up. Since we already have our 10 test items in our workflow table, we will use those.

For the test we are going to execute 3 parallel applications at the same time. In order for the test to be successful we expect that all 3 of the applications:


**1. Can query the todo items.**

**2. Can execute the task script.**

**3. Can detect items already locked by another application (ie Raise Conflicts Errors).**

**4. None of the 3 applications will execute the active TaskScript Keys value after raising a conflict error.**


```bash
# Test parallel execution
echo -e "cd /home/ec2-user" > ${wrk}/PyAnamo-Parallel-Test.txt
for i in {1..3}
	do
	echo -e "python pyanamo-beta.py ${tbl} > ${wrk}/pyanamo-beta-thread-${i}.txt"
done >> ${wrk}/PyAnamo-Parallel-Test.txt


# Execute test with 3 staggered parallel instances
parallel -j 3 < ${wrk}/PyAnamo-Parallel-Test.txt
```


### Sanity Checking Logs
The below shows the results from the parallel execution test, where 3 applications that started at the same time iterated over the 10 test items. The results show that:

**i). All parallel applications processed worked.**

**ii). All tasks encountered and handled conflicts correctly.**

```bash
# Check execution logs from each thread
wc -l pyanamo-gamma-thread*txt

"
  67 pyanamo-gamma-thread-1.txt
  79 pyanamo-gamma-thread-2.txt
  61 pyanamo-gamma-thread-3.txt
 207 total
"


# Check a specific task
grep -c "3-VC" pyanamo-gamma-thread*txt
grep "3-VC" pyanamo-gamma-thread*txt

"
pyanamo-gamma-thread-1.txt:2
pyanamo-gamma-thread-2.txt:3
pyanamo-gamma-thread-3.txt:2

pyanamo-gamma-thread-1.txt:Attempting to process 3-VC under tTqBsTDKjQHXSdz2LBwGdGjNiXVDrw
pyanamo-gamma-thread-1.txt:Conflict error on item 3-VC

pyanamo-gamma-thread-2.txt:Attempting to process 3-VC under OM3MVaDaLcNlebJPd8rsBGqJWRr2y9
pyanamo-gamma-thread-2.txt:Verification successful, processing 3-VC with seq 7
pyanamo-gamma-thread-2.txt:Execution successful, updating status and logs for 3-VC

pyanamo-gamma-thread-3.txt:Attempting to process 3-VC under HAsMEWvhSuijDg6gDLIX3mF7OcQ9zh
pyanamo-gamma-thread-3.txt:Conflict error on item 3-VC
"


# Check if any thread exited unexpectedly
grep -c "Processing complete" pyanamo-gamma-thread*txt
grep "Processing complete" pyanamo-gamma-thread*txt

"
pyanamo-gamma-thread-1.txt:1
pyanamo-gamma-thread-2.txt:1
pyanamo-gamma-thread-3.txt:1

pyanamo-gamma-thread-1.txt:Processing complete
pyanamo-gamma-thread-2.txt:Processing complete
pyanamo-gamma-thread-3.txt:Processing complete
"


# Check attempts made by each thread
grep -c "Attempting to process" pyanamo-gamma-thread*txt
# grep "Attempting to process" pyanamo-gamma-thread*txt

"
- All items were queried, and threads 1 & 3 were very competitive with each other

pyanamo-gamma-thread-1.txt:10
pyanamo-gamma-thread-2.txt:10
pyanamo-gamma-thread-3.txt:10
"


# Check conflict errors
grep -c "Conflict error on" pyanamo-gamma-thread*txt
grep "Conflict error on" pyanamo-gamma-thread*txt

"

- Conflict errors were raised by all threads for all tokens

pyanamo-gamma-thread-1.txt:7
pyanamo-gamma-thread-2.txt:5
pyanamo-gamma-thread-3.txt:8
"


# Check the work done by each thread
grep -c "Verification successful" pyanamo-gamma-thread*txt
grep "Verification successful" pyanamo-gamma-thread*txt

"
- Thread 1 processed 1,5,7 
- Thread 2 processed 0,2,3,4,6
- Thread 3 processed 8,9

pyanamo-gamma-thread-1.txt:3
pyanamo-gamma-thread-2.txt:5
pyanamo-gamma-thread-3.txt:2

pyanamo-gamma-thread-1.txt:Verification successful, processing 5-VC with seq 10
pyanamo-gamma-thread-1.txt:Verification successful, processing 7-VC with seq 12
pyanamo-gamma-thread-1.txt:Verification successful, processing 1-VC with seq 22

pyanamo-gamma-thread-2.txt:Verification successful, processing 0-VC with seq 14
pyanamo-gamma-thread-2.txt:Verification successful, processing 4-VC with seq 12
pyanamo-gamma-thread-2.txt:Verification successful, processing 3-VC with seq 7
pyanamo-gamma-thread-2.txt:Verification successful, processing 6-VC with seq 25
pyanamo-gamma-thread-2.txt:Verification successful, processing 2-VC with seq 5

pyanamo-gamma-thread-3.txt:Verification successful, processing 8-VC with seq 10
pyanamo-gamma-thread-3.txt:Verification successful, processing 9-VC with seq 24
"
```

