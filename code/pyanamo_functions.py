#!/usr/bin/python


###################################
###################################
#
# IMPORT MODULES
#
###################################
###################################


# Import modules
import boto3, random, string, re, os, time, sys, json, gzip
from boto3.dynamodb.conditions import Key, Attr
from subprocess import Popen, PIPE
from datetime import datetime
client = boto3.client('dynamodb', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')


###################################
###################################
#
# BASE FUNCTION WRAPPERS
#
###################################
###################################


# Read a file
def readFile(data):

	# Read supplied file
	with open(data, 'r') as f:
		data = [ line.rstrip('\n') for line in f ]
	f.close()
	return(data)


# Append items to import
def importItems(tbl, data):

	# Connect and initialize list
	table = dynamodb.Table(tbl)
	itemList_import = []
	importResponse = []
	itemID = 0	# Query

	# Import test data
	data = readFile(data)
	for i in data:
		taskID = i.split('|')[1]
		N = random.randint(1, 25)
		item = { "itemID": itemID, "taskID": str(taskID), "InstanceID": "", "TaskScript": str('seq ' + str(N)), "lockID": 'todo', "Log": {}, "Lock_Date": "NULL", "Done_Date": "NULL", "Log_Length": 0 }
		counter+=1
		itemList_import.append(item)
		response = table.put_item(Item = item, ReturnConsumedCapacity = 'TOTAL')
		importResponse.append(response)


	# Return response list
	return(importResponse)


# Get instanceID: Requires ec2_metadata
def getInstanceID():

	# Return batch job id if present
	if 'AWS_BATCH_JOB_ID' in os.environ:
		instanceID = os.environ['AWS_BATCH_JOB_ID'].replace(':', '-')

	# Otherwise try get instance ID
	else:
		try:
			from ec2_metadata import ec2_metadata
			instanceID = ec2_metadata.instance_id

		# Otherwise set to null
		except:
			import socket
			instanceID = str(socket.gethostname())

	return(instanceID)


#############################################
#############################################
#
# PYANAMO ENGINE FUNCTIONS
#
#############################################
#############################################


# Generate a lockID
def generateLockID():
	lockID = "".join([ random.choice(string.ascii_letters + string.digits) for i in range(30) ])
	return(lockID)



# Fetch todo items: 	Only query the itemID
def getToDoItems(tbl):

	# Initialize the ouput dictionary
	table = dynamodb.Table(tbl)
	todo = { "N": 0, "Items": [] }

	# Query the input table
	response = table.query(
		IndexName = 'ItemStateIndex',
		ProjectionExpression = "itemID, lockID, ItemState, TaskScript, taskID",
		ExpressionAttributeNames = { "#itemstate": "ItemState" },
		ExpressionAttributeValues = { ":state": "todo" },
		KeyConditionExpression = '#itemstate = :state'
	)

	# Parse results and return the dictionary
	todo["N"] = response['Count']
	todo["Items"] = response['Items']
	return(todo)



# Verify todo status of active item: 	Query all fields here
def verifyItemState(tbl, itemID, lockID, instanceID):

	# Query current state
	table = dynamodb.Table(tbl)
	currentState = table.query(
		ProjectionExpression = "ItemState",
		ExpressionAttributeNames = { "#itemID": "itemID" },
		ExpressionAttributeValues = { ":itemKey": itemID },
		KeyConditionExpression = '#itemID = :itemKey'
	)["Items"][0]


	# Lock + Verify item if still available
	if len(currentState) == 1 and currentState["ItemState"] == "todo":

		# Update the lockID + Lock_Date
		now = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
		response = table.update_item(
			Key = {'itemID': itemID},
			ExpressionAttributeNames = {
				"#lock": "lockID",
				"#state": "ItemState",
				"#DateLock": 'Lock_Date',
				"#InstanceID": 'InstanceID'
			},
			ExpressionAttributeValues = {
				":lockingID": str(lockID),
				":dateLock": str(now),
				":instanceID": str(instanceID),
				":itemstate": str('locked')
			},
			UpdateExpression="SET #lock = :lockingID, #state = :itemstate, #DateLock = :dateLock, #InstanceID = :instanceID",
			ReturnValues="UPDATED_NEW"
		)

		# Wait and retrive the current lockID
		time.sleep(random.randint(1, 4))
		currentState = table.query(
			ProjectionExpression = "lockID",
			ExpressionAttributeNames = { "#itemID": "itemID" },
			ExpressionAttributeValues = { ":itemKey": itemID },
			KeyConditionExpression = '#itemID = :itemKey'
		)["Items"][0]


		# Set verified to 1 if lockIDs match and set state to locked
		if len(currentState) == 1 and currentState["lockID"] == lockID:
			itemVerified = 1

		else:
			itemVerified = 0


	# Set verified to 0 if locked before update
	else:
		itemVerified = 0

	return(itemVerified)


# Execute & parse taskScript log
def executeTaskScript(taskScript):

	# Initialize output dict
	taskLog = {
		"Done_Date": "",
		"Log": {
			"Status": "",
			"stdout": "",
			"stderr": ""
		},
		"Log_Length": ""
	}


	# Try execute input
	try:

		# Execute and parse logs
		proc = Popen(taskScript.split(" "), stdout=PIPE, stderr=PIPE)
		stdout, stderr = proc.communicate()
		stdout = stdout.decode('utf-8')
		stderr = stderr.decode('utf-8')
		log_length = len(stdout.split("\n"))
		now = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")

		# Update output dict
		taskLog["Done_Date"] = str(now)
		taskLog["Log"]["Status"] = str("Execution Successful")
		taskLog["Log"]["stdout"] = str(stdout)
		taskLog["Log"]["stderr"] = str(stderr)
		taskLog["Log_Length"] = int(log_length)
		taskDone = 1

	# Handle execution error
	except OSError:
		now = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
		taskLog["Done_Date"] = str(now)
		taskLog["Log"]["Status"] = str("Execution Failed")
		taskDone = 0

	return(taskDone, taskLog)


# Parse out PyAnamo tags
def parsePyanamoTags(log):
	pattern = re.compile("PyAnamo:\t")
	log = list(filter(None, log.split('\n')))
	log = "\n".join(list(filter(pattern.match, log)))
	log = log.replace("PyAnamo:\t", "")
	return(log)


# Compress input to s3
def compresedPushS3(content, out, s3Bucket, s3BucketKey):

	# Compress input content
	content = bytes(content, 'utf-8')
	with gzip.open(out, 'wb') as f:
		f.write(content)

	# Push file to s3 and remove
	s3_client = boto3.client('s3')
	response = s3_client.upload_file(out, s3Bucket, s3BucketKey)
	os.remove(out)
	return("Compressed to S3 " + str("s3://" + s3Bucket + "/" + s3BucketKey))


# Handle push / updating log streams
def cloudWatchPush(taskMessage, logGroup, logStream):

	# Create log group if none
	logs = boto3.client('logs')
	response = logs.describe_log_groups(logGroupNamePrefix = logGroup)
	if len(response["logGroups"]) == 0:
		response = logs.create_log_group(logGroupName = logStream)

	# Handle updating / creating the log stream
	response = logs.describe_log_streams(logGroupName = logGroup, logStreamNamePrefix = logStream)
	if len(response["logStreams"]) == 0:

		# Create log stream
		response = logs.create_log_stream(logGroupName = logGroup, logStreamName = logStream)
		response = logs.put_log_events(logGroupName = logGroup, logStreamName = logStream, logEvents = taskMessage)
		return("Created Cloudwatch " + logGroup + logStream)

	else:

		# Otherwise update
		nextSequenceToken = response["logStreams"][0]["uploadSequenceToken"]
		response = logs.put_log_events(logGroupName = logGroup, logStreamName = logStream,
			sequenceToken = nextSequenceToken, logEvents = taskMessage
		)
		return("Updated Cloudwatch " + logGroup + logStream)


# Handle logs
def handleLogs(log, tbl, instanceID, taskID, s3Bucket):

	# Update dynamo if < 2KB
	import re
	logSize = sys.getsizeof(log)
	if logSize < 2000:
		return(["0", "DynamoDB"])

	# Direct to cloudwatch if 2KB -> 10MB
	elif logSize > 2000 and logSize < 10000000:

		# Parse out PyAnamo tags + Cloud watch push
		pyAnamoTags = parsePyanamoTags(log)
		logGroup = "/PyAnamo/"
		taskID = re.sub('_Task_[0-9]*', '', taskID)
		logStream = str(tbl + "/" + instanceID + "/" + taskID)
		taskMessage = [ { "timestamp": int(round(time.time() * 1000)), "message": "\n" + log + "\n" } ]
		response = cloudWatchPush(taskMessage, logGroup, logStream)

		# Evaluate tags size
		if sys.getsizeof(pyAnamoTags) > 2000:
			pyAnamoTags = response
		return(["1", response, pyAnamoTags])

	# Otherwise write to a compressed file and push to s3: 	Parse for PyAnamo tag if <900MB?
	else:

		# Compress to S3 file
		out = str(taskID + '-log.txt.gz')
		s3BucketKey = str("PyAnamo/" + tbl + "/" + out)
		out = compresedPushS3(log, out, s3Bucket, s3BucketKey)

		# Parse PyAnamo Tags if <900MB
		if logSize < 900000:
			pyAnamoTags = parsePyanamoTags(log)
			return(["3", out, pyAnamoTags])
		else:
			return(["3", out, out])



# Update item log
def updateItemLog(tbl, itemID, lockID, taskDone, taskLog):

	# Convert task data to string
	table = dynamodb.Table(tbl)
	# taskData = json.dumps(taskLog['Log'])

	# Handle successful tasks
	if taskDone == 1:
		response = table.update_item(
			Key = {'itemID': itemID},
			ExpressionAttributeNames = {
				"#lock": "ItemState",
				"#DateDone": 'Done_Date',
				"#LogLen": "Log_Length",
				"#Logging": "Log"
			},
			ExpressionAttributeValues = {
				":lockingID": str("done"),
				":dateDone": str(taskLog["Done_Date"]),
				":logs": taskLog['Log'],
				":logLen": int(taskLog["Log_Length"])
			},
			UpdateExpression = "SET #lock = :lockingID, #DateDone = :dateDone, #LogLen = :logLen, #Logging = :logs",
			ReturnValues="UPDATED_NEW"
		)


	# Handle failed tasks
	elif taskDone == 0:
		response = table.update_item(
			Key = {'itemID': itemID},
			ExpressionAttributeNames = {
				"#lock": "ItemState",
				"#DateDone": 'Done_Date',
				"#LogLen": "Log_Length",
				"#Logging": "Log"
			},
			ExpressionAttributeValues = {
				":lockingID": "done",
				":dateDone": str( str("Error-") + str(taskLog["Done_Date"])),
				":logs": taskLog['Log'],
				":logLen": int(taskLog["Log_Length"])
			},
			UpdateExpression = "SET #lock = :lockingID, #DateDone = :dateDone, #LogLen = :logLen, #Logging = :logs",
			ReturnValues="UPDATED_NEW"
		)


	# Return response
	return(response)



# Query Item & TaskIDs over DynamoDB Table object
def itemCounter(DynamoTable):

	# Template output dict
	itemData = { 'todo': [], 'locked': [ ], 'done': []}
	for itemState in [ 'todo', 'locked', 'done' ]:

		# Query data for Item State
		response = DynamoTable.query(
			IndexName = 'ItemStateIndex',
			ProjectionExpression = "itemID, ItemState",
			ExpressionAttributeNames = { "#lockID": "ItemState" },
			ExpressionAttributeValues = { ":lockKey": str(itemState) },
			KeyConditionExpression = '#lockID = :lockKey'
		)

		# Recursively query all data
		data = response['Items']
		while 'LastEvaluatedKey' in response:
			response = DynamoTable.query(
				ExclusiveStartKey = response['LastEvaluatedKey'],
				IndexName = 'ItemStateIndex',
				ProjectionExpression = "itemID, ItemState",
				ExpressionAttributeNames = { "#lockID": "ItemState" },
				ExpressionAttributeValues = { ":lockKey": str(itemState) },
				KeyConditionExpression = '#lockID = :lockKey'
			)
			data.extend(response['Items'])

		# Extend the item state list
		itemData[itemState].extend(data)

	# Return the item data per state
	return(itemData)



# Recurisvely scan dynamo
def recursiveGet(DynamoTable, dynamoGet_kwargs, dynamoGetMethod):

	# Handle scan / query
	if dynamoGetMethod == 'scan':

		# Scan table
		response = DynamoTable.scan(**dynamoGet_kwargs)
		data = response['Items']

		# Keep scanning until all data is fethed
		while 'LastEvaluatedKey' in response:
		    response = DynamoTable.scan(ExclusiveStartKey = response['LastEvaluatedKey'])
		    data.extend(response['Items'])

	# Otherwise query
	elif dynamoGetMethod == 'query':

		# Query table
		response = DynamoTable.query(**dynamoGet_kwargs)
		data = response['Items']

		# Keep scanning until all data is fethed
		while 'LastEvaluatedKey' in response:
		    response = DynamoTable.query(ExclusiveStartKey = response['LastEvaluatedKey'], **dynamoGet_kwargs)
		    data.extend(response['Items'])

	# Handle error
	else:
		data = 'Error'

	return(data)



# Query collection of attributes with an ItemState: Fallback to scan
def getItems(DynamoTable, itemState, itemAttribute):

	# Recursiely query
	data = []
	itemAttribute = str(", ".join(itemAttribute))
	dynamoGet_kwargs = {
		"IndexName": 'ItemStateIndex',
		"ProjectionExpression": itemAttribute,
		"ExpressionAttributeNames": { "#lockID": "ItemState" },
		"ExpressionAttributeValues": { ":lockKey": str(itemState) },
		"KeyConditionExpression": '#lockID = :lockKey'
	}
	data = recursiveGet(DynamoTable, dynamoGet_kwargs, 'query')


	# Return data object
	return(data)



######################################################
######################################################
# 
# FUNCTIONS TO MANAGE NESTED TASKS
# 
######################################################
######################################################


# Bundle tasks in the TaskScript key
def importItemsBundled(tbl, counter, data, separator, nested_delim):

	# Connect and initialize list
	itemList_import = []
	importResponse = []
	table = dynamodb.Table(tbl)
	for i in data:

		# Parse item meta data
		taskID = str(i.split(separator)[0])
		tbl = str(i.split(separator)[1])
		taskScript = str(i.split(separator)[2])
		taskArgs = str(i.split(separator)[3]).split(nested_delim)
		tasks = {}

		# Nest the task script
		for i in range(0, len(taskArgs)):
			task = { str("Task_" + str(i)): { "Status": 'todo', "Script": str(taskScript + ' ' + taskArgs[i]) } }
			tasks.update(task)

		# Import item
		item = {
			"itemID": str(counter),
			"taskID": str(taskID),
			"InstanceID": 'NULL',
			"TaskScript": tasks,
			"ItemState": 'todo',
			"lockID": "NULL",
			"Log": {},
			"Lock_Date": "NULL",
			"Done_Date": "NULL",
			"Log_Length": 0, 
			"Nested_Tasks": int(len(taskArgs)),
		}
		counter += 1
		itemList_import.append(item)
		response = table.put_item(Item = item, ReturnConsumedCapacity = 'TOTAL')
		importResponse.append(response)


	# Return response list
	return(importResponse)


# Update nested task status
def updateBundledItem(task, tbl, itemID, lockID, itemImport):

	# Handle how to update task
	table = dynamodb.Table(tbl)
	if task == 'done':

		# Execute update for setting done
		now = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
		response = table.update_item(
			Key = {'itemID': int(itemID)},
			ExpressionAttributeNames = {
				"#lock": "ItemState",
				"#DateDone": "Done_Date"
			},
			ExpressionAttributeValues = {
				":lockingID": str("done"),
				":dateDone": str(now)
			},
			UpdateExpression = "SET #lock = :lockingID, #DateDone = :dateDone",
			ReturnValues="UPDATED_NEW"
		)

	# Handle individual task
	elif task == 'single':

			# Execute update
			nestID = itemImport[0]
			taskData = itemImport[1]
			logLength = itemImport[2]
			taskScript = itemImport[3]
			response = table.update_item(
				Key = {'itemID': itemID},
				ExpressionAttributeNames = {
				"#LogLen": "Log_Length",
				"#Logging": "Log",
				"#TaskScript": "TaskScript"
				},
				ExpressionAttributeValues = {
					":logs": taskData[nestID],
					":logLen": int(logLength),
					":TaskScript": taskScript,
				},
				UpdateExpression = "SET #LogLen = :logLen, #Logging." + str(nestID) + " = :logs, #TaskScript = :TaskScript",
				ReturnValues="UPDATED_NEW"
			)

	# Handle errors
	else:
		response = "Error"


	# Return response
	return(response)

