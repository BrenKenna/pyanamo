#!/usr/bin/python


# Import modules
import boto3, random, string, os, time
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
import client as pc


# Class to modify items with
class PyAnamo_Modifier(pc.PyAnamo_Client):

	"""
		Class to Modify PyAnamo task on the supplied DynamoDB client.
		Methods includes:
			- Generating a lockID for locking todo items.
			- Getting the current instance ID; AWS-Batch, fallbacks to EC2 or IP address.
			- Locking an Item
			- Verifying that the supplied item is locked AND was locked by the active process.
			- Updating the active item on DynamoDB for Nested and Un-neseted tasks.
	"""

	# Initialize object
	def __init__(self, dynamo_table):

		# Dynamo table
		if dynamo_table is not None:
			self.dynamo_table = dynamo_table

		# PyAnamo client: Becomes useless when child inherits <= Current implementation stupid
		self.pyanamoClient = pc.PyAnamo_Client(self.dynamo_table, region = dynamo_table.table_arn.split(':')[3])


	# Generate a lockID
	def generateLockID(self):

		"""
			Generate a lockID string for conflict management
		"""

		lockID = "".join([ random.choice(string.ascii_letters + string.digits) for i in range(30) ])
		return(lockID)


	# Get instanceID
	def getInstanceID(self):

		"""
			Get the current AWS Batch Job ID, or EC2-Instance ID or Hostname
		"""

		# Return batch job id if present
		if 'AWS_BATCH_JOB_ID' in os.environ:
			instanceID = os.environ['AWS_BATCH_JOB_ID'].replace(':', '-')

		# Otherwise try get instance ID
		else:
			try:
				from ec2_metadata import ec2_metadata
				instanceID = ec2_metadata.instance_id

			# Otherwise set to null
			except ModuleNotFoundError:
				import socket
				instanceID = str(socket.gethostname())
		return(instanceID)


	# Lock Item
	def lockItem(self, itemID, lockID, instanceID):

		"""
			Lock an item from the supplied table
		"""

		# Update the lockID + Lock_Date
		now = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
		response = self.dynamo_table.update_item(
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
		# return(str(1))


	# Verify lockID
	def verifyItem(self, itemID):

		"""
			Verify that the current instance has locked the item
			Returns a Zero or a One (int) for conflict streak management in the PyAnamo_Runner
		"""

		# Check items current state and lock if available
		currentState = self.getCurrentState(itemID)['ItemState']

		# Update the lockID + Lock_Date
		if currentState == 'todo':

			# Set locking parameters
			lockID = self.generateLockID()
			instanceID = self.getInstanceID()
			self.lockItem(itemID, lockID, instanceID)

			# Wait and retrive the current lockID
			time.sleep(random.randint(1, 4))
			currentLock = self.getLockID(itemID)['lockID']
			if lockID == currentLock:
				return(1)
			else:
				return(0)
		else:
			return(0)


	# Update item log
	def updateItemLog(self, taskDone, itemID, taskLog):

		"""
			Update the supplied items Log field and mark as done
			Used by the PyAnamo_Runner
		"""

		# Handle successful tasks
		if taskDone == 1:
			response = self.dynamo_table.update_item(
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
			 	UpdateExpression = "SET #lock = :lockingID, #DateDone = :dateDone, #LogLen = :logLen, #Logging = :logs"
			)
			# response = self.dynamo_table.update_item(update_kwargs)

		# Handle failed tasks
		else:
			response = self.dynamo_table.update_item(
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
				UpdateExpression = "SET #lock = :lockingID, #DateDone = :dateDone, #LogLen = :logLen, #Logging = :logs"
			)
			# response = self.dynamo_table.update_item(update_kwargs)

		# Return response
		return(response)


	# Update nested task status
	def updateNestedItem(self, itemID, itemImport = None):

		"""
			Update the supplied nested items Log field and mark as done
			Used by the PyAnamo_Runner
		"""

		# Handle how to update task
		if itemImport is None:

			# Execute update for setting done
			now = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
			response = self.dynamo_table.update_item(
				Key = {'itemID': int(itemID)},
				ExpressionAttributeNames = {
					"#lock": "ItemState",
					"#DateDone": "Done_Date"
				},
				ExpressionAttributeValues = {
					":lockingID": str("done"),
					":dateDone": str(now)
				},
				UpdateExpression = "SET #lock = :lockingID, #DateDone = :dateDone"
			)
			# response = self.dynamo_table.update_item(update_kwargs)

		# Handle individual task
		else:

				# Update Task script
				nestID = itemImport['nestedID']
				taskLog = itemImport[nestID]['Log']
				logLength = itemImport['Log_Length']
				taskScript = itemImport[nestID]['TaskScript']
				response = self.dynamo_table.update_item(
					Key = {'itemID': itemID},
					ExpressionAttributeNames = {
						"#Logging": "Log",
						"#TaskScript": "TaskScript"
					},
					ExpressionAttributeValues = {
						":logs": taskLog,
						":TaskScript": taskScript
					},
					UpdateExpression = "SET #Logging." + str(nestID) + " = :logs, #TaskScript." + str(nestID) + " = :TaskScript"
				)

				# Increment Log_Length
				response = self.dynamo_table.update_item(
					Key = {'itemID': itemID},
					ExpressionAttributeNames = {
						"#LogLen": "Log_Length",
					},
					ExpressionAttributeValues = {
						":logLen": int(1)
					},
					UpdateExpression = "ADD #LogLen :logLen"
				)

				# response = self.dynamo_table.update_item(update_kwargs)

		# Return response
		return(response)
