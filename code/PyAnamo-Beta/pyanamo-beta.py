#!/usr/bin/python


####################################################
####################################################
#
# SETUP
#
####################################################
####################################################


# Import modules
import boto3, random, string, time, sys, json, gzip
from boto3.dynamodb.conditions import Key, Attr
from subprocess import Popen, PIPE
from datetime import datetime
from pyanamo_functions import *


# Parse input arguments
tbl = sys.argv[1]
# deleteTable = sys.argv[2]
# testing = sys.argv[3]


# Handle table
if len(tbl) == 0:

	# Exit if no table is provided
	print('\n\nExiting, no table provided\n')
	sys.exit

else:
	# Otherwise proceed	
	print('\n\nProceeding with table = ' + tbl + '\n')



######################################################################
######################################################################
#
# EXECUTE WORKFLOW
#
######################################################################
######################################################################


# Get the service resource & try connect to table
client = boto3.client('dynamodb')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table(tbl)


# Generate a lockID and fetch todo tasks
todo = getToDoItems(tbl)
N = todo["N"]


# Process tasks
for i in range(0, N):

	# Generate lockID and parse item data
	lockID = generateLockID()
	todo_item = todo["Items"][i]
	itemID = todo_item["itemID"]
	taskScript = todo_item["TaskScript"]
	taskID = todo_item["taskID"]
	print('\nAttempting to process ' + itemID + ' under ' + lockID)


	# Verify current status
	itemVerified = verifyItemState(tbl, itemID, lockID)
	if itemVerified == 1 and len(taskScript) >= 1:

		# Process item if todo status was verified
		print('\nVerification successful, processing ' + itemID + ' with ' + taskScript + '\n\n')
		taskDone, taskLog = executeTaskScript(taskScript)
		print('\nExecution successful, updating status and logs for ' + itemID + '\n\n')
		updateItemLog(tbl, itemID, lockID, taskDone, taskLog)
		time.sleep(random.randint(1, 4))

	else:

		# Otherwise continue to the next item
		print('\nConflict error on item ' + itemID)
		time.sleep(random.randint(1, 4))
		continue

print('\n\nProcessing complete\n\n')
