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
lockID = generateLockID()
todo = getToDoItems(tbl)
N = todo["N"]


# Process tasks
for i in range(0, N):

	# Parse item data
	todo_item = todo["Items"][i]
	itemID = todo_item["itemID"]
	taskScript =json.loads(todo_item["TaskScript"])
	taskID = todo_item["taskID"]
	print('\nAttempting to process ' + itemID + ' under ' + lockID)

	# Proceed with item if locking is verified
	itemVerified = verifyItemState(tbl, itemID, lockID)
	if itemVerified == 1 and len(taskScript) >= 1:

		# Iteratively execute task script keys if todo
		print('\nVerification successful, processing ' + itemID + ' with ' + json.dumps(taskScript) + '\n\n')
		taskData = []
		logLength = []
		counter = 0
		for taskKey in range(0, len(taskScript.keys())):

			# Continue to next key if done
			task = list(taskScript.keys())[taskKey]
			if taskScript[task]['Status'] != 'todo':
				print("\nSkipping task " + str(counter) + "\n")
				counter+=1
				continue


			# Proceed to execution
			print("\nProcessing task " + str(counter) + "\n")
			script = taskScript[task]["Script"]
			taskDone, taskLog = executeTaskScript(script)
			taskScript[task]['Status'] = "done"
			taskData.append(taskLog['Log'])
			logLength.append(taskLog['Log_Length'])
			counter+=1


			# Update item on DB
			updateBundledItem('single', tbl, itemID, lockID, [taskData, logLength, taskScript])


		# Update lockID and Done date before
		updateBundledItem('done', tbl, itemID, lockID, [])
		time.sleep(random.randint(1, 4))

	else:

		# Otherwise continue to the next item
		print('\nConflict error on item ' + itemID)
		time.sleep(random.randint(1, 4))
		continue

print('\n\nProcessing complete\n\n')
