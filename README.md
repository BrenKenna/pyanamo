# PyAnamo


## Introduction
The purpose of *PyAnamo* is to automate "Big Data" *'Extraction Transformation and Loading'* procedures, ETLs, on AWS using Batch &amp; DynamoDB. The principal of operation is that each requested EC2 instance executes an application that iterates over a list of work to do, *tasks*, which are stored in a database. The database is populated with various collections of tasks that represent all of the work to do from your favourite workflow. Where each individual *collection* is a step of your workflow. The database can then be queried to monitor progress of each step of the workflow.

Each task for a given collection has a *"Task Script"* key whose value is executed by a *Generic PyAnamo Application*. The setup allows for each instance of the application, running across the cluster of size N, to iteratively execute *'Program A'* on all tasks in the collection of *'Workflow Step A'*. The application could also be potentially ported into existing setups at the users own discretion, ex 'https://doi.org/10.1093/bioinformatics/btz379'.

The **advantage** in storing all of the tasks in a database, specifically for ***Population Based Reseqeucning Studies***, is that there can be ***ten's of thousands of tasks*** to keep track of across an entire workflow that can take ***~3 days to complete per sample seqenced***. These workflows usually feature a number steps that are executed on a ***'Per Sample Level'***, for example *Sequence Alignent, Downstream Read Processing, Variant Calling +/- Additional QC*. Which can then later be parallelized on the *Cohort Level* across the entire ***3 Billion Base Pairs of the Human Genome***

Adding another layer of complextity, is that fact the lists of all these various tasks are also highly *"Dynamic"* throughout a project, and largely temporary (deleted after completion). Where new samples can get sequenced / become available / drop out, or suffer some super magical technical blight during data processing, haulting their progression through the entire workflow. The cumulation of this means that one needs to be able *setup your 'ToDo' tasks in a simple manner*, and also be able to ***reliably query the workflow progress just as simply***. Which opens up the possibility in querying answers for common question like: *Which samples have been processed? How far along our workflow are we? How many samples are left to process? Which / How many samples are in step X, Y and / or Z?*



# Example

**1). Running PyAnamo**.

**2). Manage Workflow Table**.

**3). Importing / Creating PyAnamo tasks**.

**4). Managing PyAnamo Tasks (DynamoDB and/or AWS-Batch)**.

**5). Deleting / restarting PyAnamo Tasks**.

**NB: The example assumes AWS (IAM, ECR, Batch etc) and DynamoDB are setup for your account**.



## Run PyAnamo


```bash
# Run pyanamo: Non-parallel
export PYANAMO=Path/to/where/git/was/downloaded
export PYANAMO_TABLE="My_Super_Fun_Happy_Table"
S3_BUCKET=SomeName
AWS_REGION=us-east-1
python pyanamo.py -t "${PYANAMO_TABLE}" -b "${S3_BUCKET}" -r "${AWS_REGION}"


# Run pyanamo: Application process 2 items at time, and 4 nested tasks from the active item
python pyanamo.py -t "${PYANAMO_TABLE}" -b "${S3_BUCKET}" -r "${AWS_REGION}" -i '2' -n '4'
```



## Manage Workflow Table

Users can create tables, check PyAnamo's Standard Schema, check if they exist and also delete tables. The manager is also initialized with the boto3 DynamoDB resource, so that users can "swap" between tables in their region while also being able AWS-DynamoDB code over their tables. Making the manager client a "starting off" guide.


```python
# Import manager client
import manager as pmanager

# Instantiate
table_name = 'Testing'
aws_region = 'us-east-1' 
manager_client = pmanager.PyAnamo_Manager(
    dynamo_table = table_name,
    region = aws_region
)

# Check if table exists
manager_client.check_table(table_name)

# Create table
manager_client.create_workflow_table(table_name)

# Delete table
manager_client.delete_workflow_table(table_name)

# View table schema
table_exists_now = manager_client.check_table(table_name, output_schema = 1)

# Set table proberty to run Boto3-DynamoDB code on
manager_client.handle_DynamoTable('Testing')
manager_client.__dict__
manager_client.dynamo_table.__dict__['_name']

# Work on a new table
table_name = 'Testing_2'
manager_client.create_workflow_table(table_name)
manager_client.handle_DynamoTable(table_name)
manager_client.dynamo_table.__dict__['_name']
```



## Create Tasks

Examples of importing single / nested items from a file

```bash
# Write a list single items: Header and format is expected, delimiter optional
echo -e "
itemID|TaskID|TaskScript
Seq_Test_1|Task_1|seq 3
Seq_Test_2|Task_2|seq 1
Seq_Test_3|Task_3|seq 2
Seq_Test_4|Task_4|seq 10
" > import-testing.txt

# Import list of single items
python import-items.py 'Testing' 'us-east-1' 'import-testing.txt' '|'


# Write a list nested items to the same table: Delimiters optional
echo -e "
itemID|TaskID|TaskScript|TaskArgs
Seq_Test_5|Task_5|seq|8,2,1
Seq_Test_6|Task_6|seq|3,2,1
Seq_Test_7|Task_7|seq|1,4,2
Seq_Test_8|Task_8|seq|2,3,1
" > import-nested-testing.txt


# Import
python import-items.py 'Testing' 'us-east-1' 'import-nested-testing.txt' '|' ','
```



The manager client has methods for importing single and nested items, or as lists which the above is a wrapper for as shown in the below python "session".

```python
# Import manager client
import manager as pmanager

# Instantiate
table_name = 'Testing'
aws_region = 'us-east-1' 
manager_client = pmanager.PyAnamo_Manager(
    dynamo_table = table_name,
    region = aws_region
)

# Import single item
taskID = 'Task_9'
itemID = 'Seq_Test_9'
taskScript = 'seq 10'
manager_client.import_item(
	table_name = table_name,
	taskID = taskID,
	itemID = itemID,
	taskScript = taskScript
)

# Import nested item
taskID = 'Task_10'
itemID = 'Seq_Test_10'
taskScript = 'seq'
taskArgs = '10,12,14'
nested_delim = ','
manager_client.import_nested_item(
	table_name = table_name,
	taskID = taskID,
	itemID = itemID,
	taskScript = taskScript,
	taskArgs = taskArgs,
	nested_delim = nested_delim
)
```



Users can pass a list of items to import during their python "session". They can also inspect what was imported as per the wrapper script because the output is the same.  Useful if querying todo work from RDBMS ;)

```python
# Import manager client
import manager as pmanager

# Instantiate
table_name = 'Testing'
aws_region = 'us-east-1' 
manager_client = pmanager.PyAnamo_Manager(
    dynamo_table = table_name,
    region = aws_region
)

# Import list of single items
delim = '|'
data = [
	'Seq_Test_11|Task_11|seq 10',
	'Seq_Test_12|Task_12|seq 12',
	'Seq_Test_13|Task_13|seq 4',
	'Seq_Test_14|Task_14|seq 8'
]
importLog = manager_client.import_items(
    data = data,
    delim = delim,
    table_name = table_name
)

# Import list of nested items
delim = '|'
data = [
	'Seq_Test_7|Task_7|seq|3',
	'Seq_Test_8|Task_8|seq|8,7',
	'Seq_Test_9|Task_9|seq|15,16,17,3',
	'Seq_Test_10|Task_10|seq|3,2,4,6,5'
]
nested_delim = ','
Nested_importLog = manager_client.import_items(data = data, delim = delim, table_name = table_name, nested_delim = nested_delim)

# Check imports
Nested_importLog.keys()
Nested_importLog['N']
for i in Nested_importLog['Items']:
	print(i)
```



## Managing PyAnamo Tasks

Users can monitor / summarize progress of their workflow, and also view the percent progress of their nested tasks.

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
manager_client.monitor_task(table_name, Niterations = 3, waitTime = 2)

# Summarize nested tasks: Counts + itemIDs of todo, 1-25%, 26-75%, 76-99%, done
manager_client.summarize_nestedTasks(table_name)
itemSummary = manager_client.summarize_nestedTasks(table_name, output_results = 1)

# Monitor nested tasks
monitoringData = manager_client.monitor_nestedTasks(table_name, Niterations = 2, waitTime = 3)
```



### Mapping Locked Items to their AWS-Batch Job State

Users can also map the locked itemIDs to AWS-Batch job states. This allows users view which of their locked items still running jobs or Succeeded/Exited jobs on an itemID level. Since AWS-Batch only keeps their jobIDs for a certain amount of time, items locked by these jobs are also outputted.

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



## Restarting PyAnamo Tasks

```python
# Setup
import manager as pmanager
table_name = 'Testing_1'
aws_region = 'us-east-1'
manager_client = pmanager.PyAnamo_Manager(dynamo_table = table_name, region = aws_region)

# Reset item
itemID = '1'
itemState = 'todo'
out_itemUpdate = manager_client.reset_itemState(table_name = table_name, itemState = itemState, item = itemID)
print(out_itemUpdate)

# Reset item state to a desired one like 'Pending' or 'todo'
itemIDs = [ '1', '2' ]
out_itemUpdates = manager_client.reset_itemState(table_name = table_name, itemState = 'todo', item = itemIDs)

[ print(str(i) + ' = ' + str(out_itemUpdates[i])) for i in out_itemUpdates.keys() ]

# Reset a task Key for single item
itemID = 'Seq_Test_10'
taskKey = 'Task_0'
manager_client.reset_itemNest(table_name, item = itemID, taskKey = taskKey, allTasks = 0)

# For list of items reset the taskKey string
items = [
	{'itemID': 'Seq_Test_10', 'TaskScript': 'Task_0'},
	{'itemID': 'Seq_Test_9', 'TaskScript': {'Task_0': {}, 'Task_1': {} } }
]
manager_client.reset_itemNest(table_name, item = items, allTasks = 0)

# Reset all nests for list of items
items = [ 'Seq_Test_10', 'Seq_Test_9', 'Seq_Test_7', 'Seq_Test_6' ]
out = manager_client.reset_AllNests(table_name, itemList = items)
```



## Deleting PyAnamo Tasks

```python
import manager as pmanager
table_name = 'Testing'
aws_region = 'us-east-1'
manager_client = pmanager.PyAnamo_Manager(dynamo_table = table_name, region = aws_region)
manager_client.handle_DynamoTable(table_name)

# Delete whole items or specific nested tasks
manager_client.delete_nestedTasks(table_name, 'Seq_Test_7')
manager_client.delete_nestedTasks(table_name, 'Seq_Task_2', taskKey = 'Task_0')
manager_client.delete_nestedTasks(table_name, 'Seq_Task_2', taskKey = ['Task_1', 'Task_2'])

# Clear specific tasks from a list of data
itemList = [
	{'itemID': 'Seq_Test_9', 'TaskScript':['Task_0', 'Task_1']},
	{'itemID': 'Seq_Test_10', 'TaskScript':['Task_0', 'Task_1']}
]
manager_client.clear_nestedTasks(user_data['table_name'], itemList = itemList)

# Delete items
manager_client.delete_singleItem(user_data['table_name'], item = 'Seq_Test_7')
itemList = [ 'Seq_Test_7', 'Seq_Test_9', 'Seq_Test_10' ]
manager_client.delete_singleItem(user_data['table_name'], item = itemList)
```

