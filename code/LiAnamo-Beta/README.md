# LiAnamo-Beta
The purpose of this was to get the *'lay of the land'* of all things DynamoDB, whose code will ultimately get swallowed by the **PyAnamo for Aim-2**, which also extends to development suggestions such as Schema & Indexes etc.

Code requires installing the Parallel and JQ software, as well as the *"dynamo-import.txt"* located in the *"parallel_tests"* directory. Additional sub-directories and other text files are explained / referenced in this README.md


## Creating and Populating the Test Table
The below code block executes a shell script which creates the workflow and uses the global secondary indexes as defined in the *"workflow-gsi.json"*. Although the current schema is largely for debugging purposes and will be used to try additional things, the *"nuts and bolts"* of it are below. Going forward the values of the *"lockID"* key will be in the format of *"locked_${ec2_instanceID} | done_${ec2_instanceID}". Additional fields for a *"Lock_Date"* and *"Done_Date"*

itemID = Unique ID to identify an item on DynamoDB
taskID = An ID which relates the itemID to the TaskScript, ex SampleIDs
lockID = ID to manage conflicts with 3 possible values; todo, locked, done
Log = Output from executing the TaskScript value
TaskScript = What LiAnamo-Beta will exeucte if the itemID is still available


```bash
# Set vars
wrk=/home/ec2-user
db=${wrk}/aws-jobs.db
tbl="HaplotypeCaller"
mkdir -p ${wrk}/parallel_tests


# Regenerate the workflow table and import the test items
rm -f ${wrk}/${tbl}-creation-log.txt
bash create-dynamo-workflow-table.sh ${tbl} 1 1 &>> ${wrk}/${tbl}-creation-log.txt


```


## Testing Principal with 3 Parallel Aplication Instances

### Setup and Execute the Parallel Applications
Since the production environment will have thousands of distinct applications querying the one table, we need to be sure that the therory holds-up. Since we already have our 10 test items in our workflow table, we will use those.

For the test we are going to execute 3 parallel applications at the same time. In order for the test to be successful we expect that all 3 of the applications can detect Conflict Errors and that none of the 3 applications will execute the active TaskScript Keys value after flagging the conflict.


```bash
# Setup test with 3 staggered parallel instances
rm -f ${wrk}/parallel_tests/3-Simultaneous.txt
touch ${wrk}/parallel_tests/3-Simultaneous.txt
for i in $(seq 3)
	do
	echo -e "bash ${wrk}/dynamo-iterator.sh ${tbl} &>> ${wrk}/parallel_tests/Simultaneous-Thread-${i}.txt" >> ${wrk}/parallel_tests/3-Simultaneous.txt
done


# Execute test with 3 staggered parallel instances
(parallel -j 3 < ${wrk}/parallel_tests/3-Simultaneous.txt ) > ${wrk}/parallel_tests/3-Simultaneous-Logging.txt
```


### Sanity Checking Logs
The below shows the results from the parallel execution test, where 3 applications that started at the same time iterated over the 10 test items. The results show that:

**i). All parallel applications processed worked.**
**ii). All tasks encountered and handled conflicts correctly.**

```bash
# Count how often an itemID occured on all threads
grep -c "3-VC" Simultaneous-Thread*txt

"
Simultaneous-Thread-1.txt:4
Simultaneous-Thread-2.txt:1
Simultaneous-Thread-3.txt:1
"

# Count how many task scripts were executed on all threads
grep -c "Processing complete" Simultaneous-Thread*txt

"
Simultaneous-Thread-1.txt:3
Simultaneous-Thread-2.txt:3
Simultaneous-Thread-3.txt:4
"

# Count how often each thread raised a conflict error
grep -c "Exiting, task is already locked by another process" Simultaneous-Thread*txt

"
Simultaneous-Thread-1.txt:7
Simultaneous-Thread-2.txt:7
Simultaneous-Thread-3.txt:6
"


# List the taskscript that each thread executed
grep "locked task seq" Simultaneous-Thread*txt

"
Simultaneous-Thread-1.txt:Current instance = 24694 locked task seq 12 for item = 3-VC
Simultaneous-Thread-1.txt:Current instance = 24694 locked task seq 11 for item = 6-VC
Simultaneous-Thread-1.txt:Current instance = 24694 locked task seq 10 for item = 5-VC
Simultaneous-Thread-2.txt:Current instance = 28894 locked task seq 16 for item = 7-VC
Simultaneous-Thread-2.txt:Current instance = 28894 locked task seq 18 for item = 8-VC
Simultaneous-Thread-2.txt:Current instance = 28894 locked task seq 17 for item = 4-VC
Simultaneous-Thread-3.txt:Current instance = 15250 locked task seq 24 for item = 10-VC
Simultaneous-Thread-3.txt:Current instance = 15250 locked task seq 16 for item = 1-VC
Simultaneous-Thread-3.txt:Current instance = 15250 locked task seq 10 for item = 2-VC
Simultaneous-Thread-3.txt:Current instance = 15250 locked task seq 17 for item = 9-VC
"
```

