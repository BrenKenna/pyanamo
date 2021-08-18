# Using the Manager Client



## Contents

**1). Creating Workflow Tables.**

**2). Creating Tasks.**

**3). Monitoring Workflow Progress.**

**4). Managing Workflow Tasks.**



## Creating Workflow Tables

Users can create tables, check PyAnamo's Standard Schema, check if they exist and also delete tables. The manager is also initialized with the boto3 DynamoDB resource, so that users can "swap" between tables in their region while also being able to execute AWS Boto3-DynamoDB code over their tables. Making the manager client a "*starting off*" guide.

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

### Provisioning / Auto-Scaling Tables

#### Use Custom Read & Write Capacity Values for Sessions

```python
# Setup manager
import manager as pmanager
user_data = { "table_name": 'Testing_3', "aws_region": 'us-east-1' }
manager_client = pmanager.PyAnamo_Manager(dynamo_table = user_data['table_name'], region = user_data['aws_region'])


# Set read & write capacity
user_data.update( {'WriteCapacity': 70, 'ReadCapacity': 70} )
out = manager_client.set_hardProvision(user_data['table_name'], user_data['WriteCapacity'], user_data['ReadCapacity'])
```

#### Use Auto-Scaling <u>Before Deploying PyAnamo</u> + After Session

```python
# Setup manager
import manager as pmanager
user_data = { "table_name": 'Testing_3', "aws_region": 'us-east-1' }
manager_client = pmanager.PyAnamo_Manager(dynamo_table = user_data['table_name'], region = user_data['aws_region'])
manager_client.set_dynamoProperty('Testing_3')


# Register autoscaling target: NB PERFORM ONCE PER TABLE
targetRegister = manager_client.setAutoScalingTarget(user_data['table_name'], 70, 70)


# Put scaling policy on table and indexes: Target Value, ScaleDown, ScaleUp
policyLog = manager_client.putScalingPolicy(user_data['table_name'], 40, 60, 60)
```



## Creating Tasks

The manager client has methods for importing single and nested items, or as lists which the ''*import-items.py*'' script is a wrapper for,

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



Users can pass a list of items to import during their python "session". They can also inspect what was imported as per the wrapper script because the output is the same.

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



## Monitoring Workflow Progress

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

Users can also map the locked itemIDs to AWS-Batch job states. This allows users to view which of their locked items still running jobs or "*Succeeded/Exited*" jobs on an itemID level. Since AWS-Batch only keeps their jobIDs for a certain amount of time, items locked by these jobs are also outputted.

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



## Managing Workflow Tasks

### Getting Item Logs

```python
# Setup
import manager as pmanager
table_name = 'Testing_1'
aws_region = 'us-east-1'
manager_client = pmanager.PyAnamo_Manager(dynamo_table = table_name, region = aws_region)
manager_client.handle_DynamoTable(table_name)


# Get a list of fields for a specific collection of item states: todo, locked and done
done_logs = manager_client.getToDoItems('done', recursively = 0, pyanamo_fields = 'itemID, TaskID, Nested_Tasks, Log_Length, Log, ItemState')


# Get the number of returned items
done_logs['N']


# Print the keys of each returned item
for i in done_logs['Items']:
	print(i.keys())


# Get the stdout for each nested task of a specific item
itemData = done_logs['Items'][0]
itemData_second = done_logs['Items'][4]
for task in itemData['Log'].keys():
	itemData['Log'][task]['stdout']

for task in itemData_second['Log'].keys():
	itemData_second['Log'][task]['stdout']


# Check the length of stdout
for task in itemData['Log'].keys():
    task_log = itemData['Log'][task]['stdout']
    str(task + ' = ' + str(len( task_log.split('\n') )))


# Compare stdout logs of an item
len( itemData['Log']['Task_1']['stdout'].split(' ') )
len(itemData['Log']['Task_2']['stdout'].split(' '))

(itemData['itemID'] + '\t' + itemData['Log']['Task_2']['stdout']).split('\t')


# Check stderr of each nested task for an item
for task in itemData['Log'].keys():
	print(itemData['itemID'] + " stderr length = " + str(len(itemData['Log'][task]['stderr'])))
```



### Restarting PyAnamo Tasks

Items on DynamoDB have 3 states that PyAnamo works with: '*todo, locked and done*'. The PyAnamo Engine only requests items with an itemState of todo, it then tries to lock these and marks them as done once it finished where it moves onto the next one (conflicts managed during locking).

Nested tasks within an item only have 2 states which are '*todo and done*'. The PyAnamo engine only processes a nested task if its Status is todo

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



### Deleting PyAnamo Tasks

Items on DynamoDB for a given workflow table should really be looked at as being "*short-term / temporary*".

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

