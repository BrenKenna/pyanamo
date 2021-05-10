#!/usr/bin/python3


# Import modules
import argparse, boto3, random, string, time, sys, os, string, json, gzip
from boto3.dynamodb.conditions import Key, Attr
from subprocess import Popen, PIPE
from datetime import datetime
from pyanamo_functions import *
client = boto3.client('batch')
pyanamo = os.environ['PYANAMO']


# Parse input args
tbl = 'VariantCalling' # sys.argv[1]
jobQueue = "HaplotypeCaller_Queue" # sys.argv[2]


# Fetch the array IDs for a queue
jobStates = {
	'RUNNING': [],
	'SUCCEEDED': [],
	'FAILED': [],
	'PENDING': [],
	'SUBMITTED': [],
	'STARTING': [],
	'RUNNABLE': []
	
}
for jobState in jobStates.keys():
	response = client.list_jobs(jobQueue = jobQueue, jobStatus = jobState)
	[ jobStates[jobState].append(i['jobId']) for i in response['jobSummaryList'] ]

sys.stdout.write('Fetching job index states for:\n')
sys.stdout.write(json.dumps(jobStates, indent = 2, sort_keys = True))


# Merge into a single list
jobIDs = []
[ jobIDs.extend(jobStates[jobState]) for jobState in jobStates ]
len(jobIDs)


# Populate array states with a list of jobIDs
arrayStates = {
	'RUNNING': [],
	'SUCCEEDED': [],
	'FAILED': [],
	'PENDING': [],
	'SUBMITTED': [],
	'STARTING': [],
	'RUNNABLE': []
	
}
for arrayState in arrayStates:
	for jobID in jobIDs:
		response = client.list_jobs(arrayJobId = jobID, jobStatus = jobState)
		var = [ arrayStates[arrayState].append(i['jobId']) for i in response['jobSummaryList'] ]

sys.stdout.write('Quering in-active jobs from:\n')
sys.stdout.write(json.dumps(arrayStates, indent = 2, sort_keys = True))


# Pull list of completed jobIDs: N = 700
itemQueryIDs = []
[ itemQueryIDs.extend(arrayStates[jobState]) for jobState in ['SUCCEEDED', 'FAILED'] ]
len(itemQueryIDs)



# Translate the jobIDs to progress on the table
dynamo_client = boto3.client('dynamodb', region_name = 'us-east-1')
dynamodb = boto3.resource('dynamodb', region_name = 'us-east-1')
table = dynamodb.Table(tbl)
taskStates = {
	'todo': [],
	'locked': [],
	'done': []
}


# Update dict itemID and taskID stored as tuple
for jobID in itemQueryIDs:
	response = table.query(
		IndexName = 'InstanceIndex',
		ProjectionExpression = "#item, #nodeID, #lockID, #task, #itemState, #logLength",
		ExpressionAttributeNames = {
			"#item": "itemID",
			"#task": "taskID",
			"#nodeID": "InstanceID",
			"#lockID": "lockID",
			"#itemState": "ItemState",
			"#logLength": "Log_Length"
		},
		ExpressionAttributeValues = { ":node": str(jobID.replace(':', '-')) },
		KeyConditionExpression = '#nodeID = :node'
	)['Items'][0]
	data = (int(response['itemID']), response['taskID'], int(response['Log_Length']))
	if response['ItemState'] == 'todo':
		taskStates['todo'].append(data)
	elif response['ItemState'] == 'done':
		taskStates['done'].append(data)
	elif response['ItemState'] == 'locked':
		taskStates['locked'].append(data)
	else:
		pass

# Summarize dict
sys.stdout.write('Restarting locked items from inactive jobs:\n')
sys.stdout.write(json.dumps(taskStates, indent = 2, sort_keys = True))


# Update locked tasks to 'todo' for finished jobs
responseList = []
for data in taskStates['locked']:
	response = table.update_item(
		Key = {'itemID': data[0]},
		ExpressionAttributeNames = {
			"#itemState": "ItemState",
			"#DateLock": 'Lock_Date'
		},
		ExpressionAttributeValues = {
			":ItemState": str('todo'),
			":dateLock": None,
		},
		UpdateExpression="SET #itemState = :ItemState, #DateLock = :dateLock",
		ReturnValues="UPDATED_NEW"
	)
	responseList.append(response)
str('Resetted N = ' + str(len(responseList)) + ' items')
