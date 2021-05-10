#!/usr/bin/python3


# Import modules
import argparse, boto3, random, string, time, sys, os, string, json, gzip
from boto3.dynamodb.conditions import Key, Attr
from subprocess import Popen, PIPE
from datetime import datetime
from pyanamo_functions import *
pyanamo = os.environ['PYANAMO']


# Parse input args
tbl = 'VariantCalling' # sys.argv[1]
jobQueue = "HaplotypeCaller_Queue" # sys.argv[2]
client = boto3.client('batch')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table(tbl)


# Query instanceIDs of locked tasks
lockedItems = table.query(
	IndexName = 'InstanceStateIndex',
	ProjectionExpression = "#item, #nodeID, #task, #itemState, #logLength",
	ExpressionAttributeNames = {
		"#item": "itemID",
		"#task": "taskID",
		"#nodeID": "InstanceID",
		"#itemState": "ItemState",
		"#logLength": "Log_Length"
	},
	ExpressionAttributeValues = { ":ItemState": 'locked' },
	KeyConditionExpression = '#itemState = :ItemState'
)['Items']
print('Checking aws states associated with N items = ' + str(len(lockedItems)))


# Get done / failed jobIDs
# jobIDs = list(set([ task['InstanceID'].replace('-', ':')  ]))
# response = client.describe_jobs(jobs = jobIDs))['jobs']
unlockItems = []
for task in lockedItems:
	jobID = '-'.join(task['InstanceID'].split('-')[0:-1])
	jobID = str(jobID + ':' + task['InstanceID'].split('-')[-1])
	response = client.describe_jobs(jobs = [jobID])['jobs'][0]
	if response['status'] == 'SUCCEEDED' or response['status'] == 'FAILED':
		unlockItems.append(int(task['itemID']))


# Update locked tasks to 'todo' for finished jobs: Consider ItemStateIndex as PK
print('Unlocking N items = ' + str(len(unlockItems)))
responseList = []
while len(unlockItems)!= 0:
	itemID = int(unlockItems.pop(0))
	response = table.update_item(
		Key = {'itemID': itemID},
		ExpressionAttributeNames = {
			"#lock": "lockID",
			"#state": "ItemState",
			"#DateLock": 'Lock_Date',
			"#InstanceID": 'InstanceID'
		},
		ExpressionAttributeValues = {
			":lockingID": 'NULL',
			":dateLock": 'NULL',
			":instanceID": 'NULL',
			":itemstate": str('todo')
		},
		UpdateExpression = "SET #lock = :lockingID, #state = :itemstate, #DateLock = :dateLock, #InstanceID = :instanceID",
		ReturnValues = "UPDATED_NEW"
	)
	responseList.append(response)

