#!/usr/bin/python


# Import modules
import boto3, random, os, json, time, random
from boto3.dynamodb.conditions import Key, Attr
dynamodb_client = boto3.client('dynamodb')
import client as pc


# Class to interact with a Dynamo table object
class PyAnamo_Manager(pc.PyAnamo_Client):

	"""
		Class for the day-to-day management of PyAnamo tasks, which extends the PyAnamo_Client
		The PyAnamo_Manager includes methods to:

			### USE kwargs for Dynamo a little (reset items) ###
			### Dump imports etc to manager_helper ###

			# Create / Remove workflow table (Manager)
			# Describe the workflow table schema (Manager)
			# Set dynamo_table property
			- Alter table provisioning and set auto-scaling (Manager)
			# Check whether specific items do or do not exist (Manager + Client-getCurrentState)
			# Import task, list or text file of tasks to table (Manager)
			# Summarize the PyAnamo item states (optionally over-time) (Manager + Client-itemCounter)
			- Monitor nested tasks: {
					0% / todo: { N, [] },
					1-25%: { N, [] },
					26-49%: { N, [] },
					50-74%: { N, [] },
					75-99%: { N, [] },
					100% / done: { N, [] }
			}
			# Change item states (optionally user-defined string (Manager + Client)
			- Retrieve item logs, instanceIDs (Manager + Client-getToDoItems)
			- Translate itemStates to AWS-Batch job states (Manager + Client)
			# Unlock / Restart tasks (Manager)
			- Unlock specific nested tasks within specific items (Manager)
			- Delete specific items / nests in items (Client)
			- Template for managing custom priority queue (itemStates + monitoring over time) (Manager + Client)
	"""

	# Initialize object
	def __init__(self, dynamo_table = None, region = None):

		# Dynamo
		self.region = region
		if type(dynamo_table) is str:
			self.dynamodb = boto3.resource('dynamodb', region_name = region)

		elif type(dynamo_table) is not str:
			self.dynamo_table = dynamo_table


	# Set dynamoDB table proberty to self
	def set_dynamoProperty(self, table_name):

		# Set property and log to user
		try:
			self.dynamo_table = self.dynamodb.Table(table_name)
			check = self.dynamo_table.__dict__['_name']
			out = str('Dynamo Table Object now = ' + check)
		except:
			out = str('Error setting table = ' + table_name + ', please check that it exists')
		return(out)


	# Handle dynamo_table object
	def handle_DynamoTable(self, table_name):

		# Check table object is a property
		if 'dynamo_table' in self.__dict__:

			# Only update if table names do not match
			currentTable = self.dynamo_table.__dict__['_name']
			if currentTable != table_name:
				out = self.set_dynamoProperty(table_name)
				return(out)

		# Otherwise set
		else:
			out = self.set_dynamoProperty(table_name)
			return(out)


	# Check if table exists
	def check_table(self, table_name, output_schema = None):

		# Try describe table
		try:

			# Return 1 if works
			response = dynamodb_client.describe_table(TableName = table_name)
			out = 1

			# Handle
			if 'Table' in response and output_schema != None:
				out = response['Table']

			# Otherwise return status
			return(out)

		# Otherwise return 0
		except dynamodb_client.exceptions.ResourceNotFoundException:
			out = int(0)
			return(out)


	# Read local json file
	def read_jsonFile(self, data):
		with open(data) as json_file:
				out = json.load(json_file)
		return(out)


	# Create table
	def create_workflow_table(self, table_name):

		# Try read json otherwise use template
		pyanamoTableTemplate = str(os.environ['PYANAMO'] + '/workflow-gsi-index.json')
		try:
			table_GSI = self.read_jsonFile(pyanamoTableTemplate)
	
		except FileNotFoundError:
			table_GSI = [{'IndexName': 'ItemStateIndex', 'KeySchema': [{'AttributeName': 'ItemState', 'KeyType': 'HASH'}, {'AttributeName': 'itemID', 'KeyType': 'RANGE'}], 'Projection': {'ProjectionType': 'ALL'}, 'ProvisionedThroughput': {'ReadCapacityUnits': 10, 'WriteCapacityUnits': 5}}, {'IndexName': 'TaskStateIndex', 'KeySchema': [{'AttributeName': 'ItemState', 'KeyType': 'HASH'}, {'AttributeName': 'taskID', 'KeyType': 'RANGE'}], 'Projection': {'ProjectionType': 'ALL'}, 'ProvisionedThroughput': {'ReadCapacityUnits': 10, 'WriteCapacityUnits': 5}}, {'IndexName': 'InstanceStateIndex', 'KeySchema': [{'AttributeName': 'ItemState', 'KeyType': 'HASH'}, {'AttributeName': 'InstanceID', 'KeyType': 'RANGE'}], 'Projection': {'ProjectionType': 'ALL'}, 'ProvisionedThroughput': {'ReadCapacityUnits': 10, 'WriteCapacityUnits': 5}}, {'IndexName': 'LoggingIndex', 'KeySchema': [{'AttributeName': 'ItemState', 'KeyType': 'HASH'}, {'AttributeName': 'Log_Length', 'KeyType': 'RANGE'}], 'Projection': {'ProjectionType': 'ALL'}, 'ProvisionedThroughput': {'ReadCapacityUnits': 10, 'WriteCapacityUnits': 5}}]


		# Set table schema
		table_KeySchema = [  
			{ "AttributeName": "itemID", "KeyType": "HASH" }
		]
		table_AttributeSchema = [
			{ 'AttributeName': "itemID", "AttributeType": "S" },
			{ 'AttributeName': "ItemState", "AttributeType": "S" },
			{ 'AttributeName': "taskID", "AttributeType": "S" },
			{ 'AttributeName': "InstanceID", "AttributeType": "S" },
			{ 'AttributeName': "Log_Length", "AttributeType": "N" }
		]
		table_Provisioning = { 'ReadCapacityUnits': 10, 'WriteCapacityUnits': 10 }


		# Create table if not exists
		table_exists = self.check_table(table_name)
		if table_exists == 0:
			print('Creating table = ' + table_name)
			dynamo_table = self.dynamodb.create_table(
				TableName = table_name,
				KeySchema = table_KeySchema,
				AttributeDefinitions = table_AttributeSchema,
				GlobalSecondaryIndexes = table_GSI,
				ProvisionedThroughput = table_Provisioning
			)
			time.sleep(int(10))
			print('Table = ' + table_name + ' created')
			out = int(1)


		# Otherwise log table already exists
		else:
			print('Table = ' + table_name + ' already exists')
			out = int(0)

		return(out)


	# Delete workflow table
	def delete_workflow_table(self, table_name):

		# Delete table if exists
		table_exists = self.check_table(table_name)
		if table_exists == 1:
			self.handle_DynamoTable(table_name)
			self.dynamo_table.delete()
			time.sleep(int(10))
			out = int(1)
			print('Table = ' + table_name + ' deleted')

		# Otherwise log non-existent
		else:
			out = int(0)
			print('Table = ' + table_name + ' does not exist')
		return(out)


	# Monitor tasks
	def monitor_task(self, table_name, Niterations = 1, waitTime = 0):

		# Handle table object
		self.handle_DynamoTable(table_name)

		# Run item counter for N iterations, with wait time between them		
		N = 0
		while N < Niterations:

			# Get item IDs per state
			N += 1
			taskSummary = {}
			itemData = self.itemCounter(self.dynamo_table)

			# Populate taskSummary
			if itemData['ItemCount'] > 0:
				for itemState in [ 'todo', 'locked', 'done' ]:
					stateN = len(itemData[itemState])
					taskSummary.update( { itemState: int(stateN) } )

				# Wait and return results
				time.sleep(int(waitTime))
				return(taskSummary)

			# Otherwise log
			else:
				print('No items retrived from table = ' + table_name)


	# Set itemStates
	def updateItemStates(self, table_name, itemID_list, itemState):

		# Iteratively update the list of items to itemState
		self.handle_DynamoTable(table_name)
		counter = 0
		failedItems = []
		for itemID in itemID_list:

			# Change state
			try:
				response = self.dynamo_table.update_item(
					Key = {'itemID': itemID},
					ExpressionAttributeNames = { "#state": "ItemState" },
					ExpressionAttributeValues = { ":itemstate": str(itemState) },
					UpdateExpression = "SET #state = :itemstate",
					ReturnValues="UPDATED_NEW"
				)
				counter += 1
			except:
				failedItems.append(itemID)

		# Log status
		print('Successfully update N = ' + str(counter) + " items to state = " + itemState + " and failed to update N = " + str(len(failedItems)) + " items")
		return(failedItems)


	# Import single item
	def import_item(self, table_name = None, taskID = None, itemID = None, taskScript = None):

		# Parse input
		if table_name is None or taskID is None or itemID is None or taskScript is None:
			print('Error, please provide table name, taskID, itemID, and a taskScript')

		# Otherwise proceed
		else:

			# Construct itemDict
			itemDict = {
				"itemID": str(itemID),
				"taskID": str(taskID),
				"TaskScript": str(taskScript),
				"lockID": "NULL",
				"ItemState": "todo",
				"Lock_Date": "NULL",
				"Done_Date": "NULL",
				"Log": {},
				"Log_Length": 0
			}

			# Import item
			try:
				self.handle_DynamoTable(table_name)
				response = self.dynamo_table.put_item(Item = itemDict, ReturnConsumedCapacity = 'TOTAL')
				return(itemDict)
			except:
				print('Error importing itemID = ' + str(itemID))


	# Import single nested item
	def import_nested_item(self, table_name = None, taskID = None, itemID = None, taskScript = None, taskArgs = None, nested_delim = None):

		# Parse input
		if table_name is None or taskID is None or itemID is None or taskScript is None or nested_delim is None:
			print('Error, please provide table name, taskID, itemID, taskScript, taskArgs and nested delimiter for taskArgs')

		# Otherwise proceed
		else:

			# Nest the task script
			taskArgs = str(taskArgs).split(nested_delim)
			tasks = {}
			for i in range(0, len(taskArgs)):
				task = {
					str('Task_' + str(i)): {
						"Status": 'todo',
						"Script": str(taskScript + ' ' + taskArgs[i]).replace('  ', ' ')
					}
				}
				tasks.update(task)

			# Construct the itemDict
			itemDict = {
				"itemID": str(itemID),
				"taskID": str(taskID),
				"TaskScript": tasks,
				"lockID": "NULL",
				"ItemState": "todo",
				"Lock_Date": "NULL",
				"Done_Date": "NULL",
				"Log": {},
				"Log_Length": 0,
				"Nested_Tasks": int(len(taskArgs))
			}


			# Import item
			try:
				self.handle_DynamoTable(table_name)
				response = self.dynamo_table.put_item(Item = itemDict, ReturnConsumedCapacity = 'TOTAL')
				return(itemDict)
			except:
				print('Error importing itemID = ' + str(itemID))



	# Import items
	def import_items(self, data = [], delim = None, table_name = None, nested_delim = None):

		# Handle inputs
		if data is None or delim is None or table_name is None:
			print('Please provide data in the form of "itemID|taskID|TaskScript|TaskArgs" or as file of same format, delimiter for the task data and a table_name')

		# Otherwise proceed
		else:

			# Handle data as file
			out = {'N': 0, 'Items': [ ] }
			if os.path.isfile(str(data)):
				pass

			# Handle as string
			elif type(data) is list and delim is not None:

				# Iteratively import
				for item in data:

					# Set fields
					out['N'] += 1
					itemID = item.split(delim)[0]
					taskID = item.split(delim)[1]
					taskScript = item.split(delim)[2]

					# Determine how to handle item
					if nested_delim is None:

						# Import as single item
						print('Importing as single item')
						log = self.import_item(table_name = table_name, taskID = taskID, itemID = itemID, taskScript = taskScript)
						out['Items'].append(log)

					# Handle as nested
					else:
						print('Importing as nested item')
						taskArgs = item.split(delim)[3]
						log = self.import_nested_item(table_name = table_name, taskID = taskID, itemID = itemID, taskScript = taskScript, taskArgs = taskArgs, nested_delim = nested_delim)
						out['Items'].append(log)

			# Otherwise pass
			else:
				out = str('Error parsing provided data and delimiter')


			# Return out
			return(out)


	# Restart items
	def reset_itemState(self, table_name = None, itemState = None, item = []):

		# Handle arguments
		if table_name is None or itemState is None or item == []:
			print('Error, please provide table_name, an item / item list and a state to set items')


		# Otherwise proceed
		else:

			# Update the list of items
			self.handle_DynamoTable(table_name)
			if type(item) is list:

				# Try setting item states
				out = {'N': 0, 'Updated': [], 'Failed': []}
				for itemID in item:
					out['N'] += 1
					try:
						response = self.dynamo_table.update_item(
							Key = {'itemID': str(itemID)},
							ExpressionAttributeNames = {
								"#lock": "lockID",
								"#state": "ItemState",
								"#DateLock": 'Lock_Date',
								"#DateDone": 'Done_Date',
								"#InstanceID": 'InstanceID',
								"#Logging": 'Log',
								"#Log_Len": 'Log_Length'
							},
							ExpressionAttributeValues = {
								":lockingID": "NULL",
								":dateLock": "NULL",
								":instanceID": "NULL",
								":itemstate": str(itemState),
								":logging": {},
								":dateDone": "NULL",
								":log_len": int(0)
							},
							UpdateExpression = "SET #lock = :lockingID, #state = :itemstate, #DateLock = :dateLock, #DateDone = :dateDone, #InstanceID = :instanceID, #Logging = :logging, #Log_Len = :log_len",								
							ReturnValues = "UPDATED_NEW"
						)
						out['Updated'].append(str(itemID))

					# Otherwise add to failed
					except:
						out['Failed'].append(str(itemID))

			# Otherwise update the supplied item
			else:
				try:
					response = self.dynamo_table.update_item(
						Key = {'itemID': str(item)},
						ExpressionAttributeNames = {
							"#lock": "lockID",
							"#state": "ItemState",
							"#DateLock": 'Lock_Date',
							"#DateDone": 'Done_Date',
							"#InstanceID": 'InstanceID',
							"#Logging": 'Log',
							"#Log_Len": 'Log_Length'
						},
						ExpressionAttributeValues = {
							":lockingID": "NULL",
							":dateLock": "NULL",
							":instanceID": "NULL",
							":itemstate": str(itemState),
							":logging": {},
							":dateDone": "NULL",
							":log_len": int(0)
						},
						UpdateExpression = "SET #lock = :lockingID, #state = :itemstate, #DateLock = :dateLock, #DateDone = :dateDone, #InstanceID = :instanceID, #Logging = :logging, #Log_Len = :log_len",
						ReturnValue = "UPDATED_NEW"
					)
					out = str('Updated item = ' + item)

				# Otherwise add to failed
				except:
					out = str('Error updating item = ' + item)

			# Return out 
			return(out)

	# Reset nest in item
	def reset_itemNest(self, table_name, item = [], allTasks = 1, taskKey = None):

		# Handle inputs
		if table_name is None or item is None:
			print('Error, please provide table_name, item as a dict / list, or taskKey or allTasks')

		# Handle items as a list
		if type(item) is list:

			# Verify first item
			if type(item[0]) is tuple:

				# Parse list as tuple of: itemID, [tasks]
				for i in item:
					itemID = i[0]
					tasks = i[1]
					
					# Handle tasks as list
					if type(tasks) != list:

						# Set the itemIDs taskScript.tasks.Status = todo

					else:

						# Iteratively update the task
						for task in task:

							# Set the itemIDs taskScript.task.Status = todo

			# Otherwise reset all nested tasks
			elif allTasks == 1:
				for itemID in item:

					# Get the taskScript for item

					# Set each taskScript keys status to todo

			# Otherwise log error
			else:
				out = 'Error, invalid format please provide items as a list of tuples (itemID, [tasks]) or list of itemIDs and DO NOT UPDATE allTasks = 1'	

		# Handle resetting all taskscript keys
		elif allTasks = 1:
				# Get the itemIDs taskScript

				# Rest task Keys

		# Handle specific taskKey
		elif taskKey != None:
			# Set the itemIDs taskKey 


		# Otherwise report error
		else:
			out = str('Error, not enough arguments supplied')


		# Return out
		return(out)
