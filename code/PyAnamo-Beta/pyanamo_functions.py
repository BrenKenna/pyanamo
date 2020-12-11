#!/usr/bin/python


###################################
###################################
#
# IMPORT MODULES
#
###################################
###################################


# Import modules
import boto3, random, string, time, sys, json, gzip
from boto3.dynamodb.conditions import Key, Attr
from subprocess import Popen, PIPE
from datetime import datetime
client = boto3.client('dynamodb')
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



# Wait until the table exists: 	What other stuff is in meta?
# table.meta.client.get_waiter('table_exists').wait(TableName = tbl)



# Append items to import
def importItems(tbl, data):

	# Connect and initialize list
	table = dynamodb.Table(tbl)
	itemList_import = []
	importResponse = []
	counter=0

	# Import test data
	data = readFile(data)
	for i in data:
		itemID = str(str(counter) + '-VC')
		taskID = i.split('|')[1]
		N = random.randint(1, 25)
		item = { "itemID": str(itemID), "taskID": str(taskID), "ID_Index": str(counter), "TaskScript": str('seq ' + str(N)), "lockID": 'todo', "Log": "NULL", "Lock_Date": "NULL", "Done_Date": "NULL", "Log_Length": "NULL" }
		counter+=1
		itemList_import.append(item)
		response = table.put_item(Item = item, ReturnConsumedCapacity = 'TOTAL')
		importResponse.append(response)


	# Return response list
	return(importResponse)



###################################
###################################
#
# PYANAMO ENGINE FUNCTIONS
#
###################################
###################################


# Generate a lockID
def generateLockID():
	lockID = "".join([ random.choice(string.ascii_letters + string.digits) for i in range(30) ])
	return(lockID)



# Fetch todo items
def getToDoItems(tbl):

	# Initialize the ouput dictionary
	table = dynamodb.Table(tbl)
	todo = { "N": 0, "Items": [] }

	# Query the input table
	response = table.query(
		IndexName = 'LoggingIndex',
		ProjectionExpression = "itemID, lockID, TaskScript, taskID",
		ExpressionAttributeNames = { "#lockID": "lockID" },
		ExpressionAttributeValues = { ":lockKey": "todo" },
		KeyConditionExpression = '#lockID = :lockKey'
	)

	# Parse results and return the dictionary
	todo["N"] = response['Count']
	todo["Items"] = response['Items']
	return(todo)



# Verify todo status of active item
def verifyItemState(tbl, itemID, lockID):

	# Query current state
	table = dynamodb.Table(tbl)
	currentState = table.query(
		ProjectionExpression = "lockID",
		ExpressionAttributeNames = { "#itemID": "itemID" },
		ExpressionAttributeValues = { ":itemKey": itemID },
		KeyConditionExpression = '#itemID = :itemKey'
	)["Items"][0]


	# Lock + Verify item if still available
	if len(currentState) == 1 and currentState["lockID"] == "todo":

		# Update the lockID + Lock_Date
		now = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
		response = table.update_item(
			Key = {'itemID': itemID},
			ExpressionAttributeNames = { "#lock": "lockID", "#DateLock": 'Lock_Date' },
			ExpressionAttributeValues = { ":lockingID": str(lockID), ":dateLock": str(now) },
			UpdateExpression="SET #lock = :lockingID, #DateLock = :dateLock",
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


		# Set verified to 1 if lockIDs match
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
		proc = Popen(taskScript.split(), stdout=PIPE, stderr=PIPE)
		now = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
		stdout, stderr = proc.communicate()
		stdout = stdout.decode('ascii')
		stderr = stderr.decode('ascii')
		log_length = len(stdout.split("\n"))

		# Update output dict
		taskLog["Done_Date"] = str(now)
		taskLog["Log"]["Status"] = str("Execution Successful")
		taskLog["Log"]["stdout"] = str(stdout)
		taskLog["Log"]["stderr"] = str(stderr)
		taskLog["Log_Length"] = str(log_length)
		taskDone = 1

	# Handle execution error
	except OSError:
		now = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
		taskLog["Done_Date"] = str(now)
		taskLog["Log"]["Status"] = str("Execution Failed")
		taskDone = 0

	return(taskDone, taskLog)



# Update item log
def updateItemLog(tbl, itemID, lockID, taskDone, taskLog):

	# Convert task data to string
	table = dynamodb.Table(tbl)
	taskData = json.dumps(taskLog['Log'])


	# Handle successful tasks
	if taskDone == 1:
		response = table.update_item(
			Key = {'itemID': itemID},
			ExpressionAttributeNames = { "#lock": "lockID", "#DateDone": 'Done_Date', "#LogLen": "Log_Length", "#Logging": "Log" },
			ExpressionAttributeValues = { ":lockingID": str("Done_" + lockID), ":dateDone": str(taskLog["Done_Date"]), ":logs": taskData, ":logLen": str(taskLog["Log_Length"]) },
			UpdateExpression = "SET #lock = :lockingID, #DateDone = :dateDone, #LogLen = :logLen, #Logging = :logs",
			ReturnValues="UPDATED_NEW"
		)

	# Handle failed tasks
	elif taskDone == 0:
		response = table.update_item(
			Key = {'itemID': itemID},
			ExpressionAttributeNames = { "#lock": "lockID", "#DateDone": 'Done_Date', "#LogLen": "Log_Length", "#Logging": "Log" },
			ExpressionAttributeValues = { ":lockingID": str("Done_" + lockID), ":dateDone": str( str("Error-") + str(taskLog["Done_Date"])), ":logs": taskData, ":logLen": str(str(taskLog["Log_Length"])) },
			UpdateExpression = "SET #lock = :lockingID, #DateDone = :dateDone, #LogLen = :logLen, #Logging = :logs",
			ReturnValues="UPDATED_NEW"
		)


	# Return response
	return(response)
