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

			# Alter table provisioning
			# Set auto-scaling
			# Import from file
			# Translate itemStates to AWS-Batch job states
			# Create / Remove workflow table
			# Describe the workflow table schema
			# Set dynamo_table property
			# Check whether specific items do or do not exist
			# Import task, list or text file of tasks to table
			# Summarize item states
			# Summarize progress of nested tasks
			# Monitor nested tasks
			# Change item states
			# Retrieve item logs, instanceIDs
			# Unlock / Restart tasks
			# Unlock specific nested tasks within specific items
			# Delete specific items / nests in items
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
		"""
			Set a DynamoDB Table proberty to self if table exists
		"""

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
		"""
			Simple wrapper to handle swapping between DynamoDB tables with that provided
		"""

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
		"""
			Return a 0 or 1 for whether or not supplied table exists, optionally output schema 
		"""

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
		"""
			Read input json file, ie a users custom changes to the workflow-gsi.json
		"""
		with open(data) as json_file:
				out = json.load(json_file)
		return(out)


	# Read a file
	def readFile(self, data, line_delim = '\n'):
		"""
			Read input text file with default line delimiter of new line. For item imports
		"""
		with open(data, 'r') as f:
			data = [ line.rstrip(line_delim) for line in f ]
		f.close()
		return(data)


	# Create table
	def create_workflow_table(self, table_name):
		"""
			Create table if not exists
		"""

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
		"""
			Delete table if exists
		"""

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
		"""
			Monitor task table for a number of iterations waiting supplied seconds after iteration
		"""

		# Handle table object
		self.handle_DynamoTable(table_name)

		# Run item counter for N iterations, with wait time between them		
		N = 0
		taskSummary = {}
		while N < Niterations:

			# Get item IDs per state
			iterID = str("Iteration_" + str(N))
			iterSummary = { iterID: {'todo': 0, 'locked': 0, 'done': 0} }
			N += 1
			itemData = self.itemCounter(self.dynamo_table)

			# Populate taskSummary
			if itemData['ItemCount'] > 0:
				for itemState in [ 'todo', 'locked', 'done' ]:
					stateN = len(itemData[itemState])
					iterSummary[iterID][itemState] = stateN
					taskSummary.update(iterSummary)

				# Wait and return results
				print(iterSummary)
				time.sleep(int(waitTime))

			# Otherwise log
			else:
				print('No items retrived from table = ' + table_name)

		# Return taskSummary
		return(taskSummary)


	# Set itemStates
	def updateItemStates(self, table_name, itemID_list, itemState):
		"""
			Update the workflow table table itemID string / list with itemState
		"""

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
		"""
			Import the supplied item data into the workflow table
		"""

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
		"""
			Import supplied item data as a nested task to the workflow table
		"""

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
		"""
			Wrapper to handle importing a list of single / nested task Items
		"""

		# Handle inputs
		if data is None or delim is None or table_name is None:
			print('Please provide data in the form of "itemID|taskID|TaskScript|TaskArgs" or as file of same format, delimiter for the task data and a table_name')

		# Otherwise proceed
		else:

			# Handle iterative imports
			out = {'N': 0, 'Items': [ ] }
			if type(data) is list and delim is not None:

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
						log = self.import_item(table_name = table_name, taskID = taskID, itemID = itemID, taskScript = taskScript)
						out['Items'].append(log)

					# Handle as nested
					else:
						taskArgs = item.split(delim)[3]
						log = self.import_nested_item(table_name = table_name, taskID = taskID, itemID = itemID, taskScript = taskScript, taskArgs = taskArgs, nested_delim = nested_delim)
						out['Items'].append(log)

			# Otherwise pass
			else:
				out = str('Error parsing provided data and delimiter')


			# Return out
			return(out)


	# Import from file
	def import_from_file(self, table_name = None, data = None, delim = None, nested_delim = None, force_import = 0):
		"""
			Wrapper to handle import single / nested task items from a text file. Can force_import = 1 if imports match standard format
		"""

		# Handle arguments
		if os.path.exists(data) == True:
			data = self.readFile(data)
			data = list(filter(None, data))

			# Check header or force import
			if 'itemID' in data[0].split(delim) or force_import == 1:

				# Import as single item
				if nested_delim is None:

					# Handle force
					if force_import == 0:
						print('Importing as single items N = ' + str(len(data[1::])) )
						out = self.import_items(data = data[1::], delim = delim, table_name = table_name)
					else:
						print('Importing as single items N = ' + str(len(data)) )
						out = self.import_items(data = data, delim = delim, table_name = table_name)

				# Import as nested
				elif nested_delim is not None:

					# Handle force import
					if force_import == 0:
						print('Importing as nested items N = ' + str(len(data[1::])) )
						out = self.import_items(data = data[1::], delim = delim, table_name = table_name, nested_delim = nested_delim)
					else:
						print('Importing as nested items N = ' + str(len(data)) )
						out = self.import_items(data = data, delim = delim, table_name = table_name, nested_delim = nested_delim)

				# Otherwise log undetermined import mode
				else:
					out = str('Error, unable to determine how to import data. If single items please use itemID|Task_ID|TaskScript and specifiy your delimiter. If nested please append please use itemID|Task_ID|TaskScript|TaskArgs and specifiy both the delimiter and the TaskArgs delimiter')


			# Otherwise log malformed header
			else:
				out = str('Error, file imports must contain a header and be of the format: itemID|TaskID|TaskScript if nesting then TaskArgs proceeds the TaskScipt with your delimiter')


		# Otherwise log file not found
		else:
			out = str('Error input file = ' + data + ' not found')

		# Return output
		return(out)


	# Restart items
	def reset_itemState(self, table_name = None, itemState = None, item = []):
		"""
			Set a desired state for a string / list of items
		"""

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


	# Update item nest
	def updateNestedItemState(self, table_name = None, itemID = None, taskKey = None):
		"""
			Set nested tasks to a 'todo' state for the provided itemID and taskKey
		"""

		# Handle arguments
		if table_name is None or itemID is None or taskKey is None:
			print('Error, please provide a table_name, itemID and a taskKey within a taskScript to update')

		# Otherwise proceed
		else:

			# Update status
			self.handle_DynamoTable(table_name)
			response = self.dynamo_table.update_item(
				Key = {'itemID': str(itemID)},
				ExpressionAttributeNames = {
					"#taskScript": "TaskScript",
					"#taskKey": str(taskKey),
					"#taskStatus": 'Status',
					"#lock": "lockID",
					"#state": "ItemState",
					"#InstanceID": 'InstanceID'
				},
				ExpressionAttributeValues = {
					":instanceID": "NULL",
					":lockingID": "NULL",
					":itemstate": str('todo'),
					":TaskStatus": str('todo')
				},
				UpdateExpression = "SET #lock = :lockingID, #state = :itemstate, #InstanceID = :instanceID, #taskScript.#taskKey.#taskStatus = :TaskStatus"
			)

			# Delete task Key from log
			response = self.dynamo_table.update_item(
				Key = {'itemID': str(itemID)},
				ExpressionAttributeNames = {
					"#Logging": 'Log',
					"#taskLogging": str(taskKey)
				},
				UpdateExpression = "REMOVE #Logging.#taskLogging"
			)
			out = str('Updated item = ' + str(itemID) + ' taskKey = ' + str(taskKey))

			# Log out
			return(out)

	# Reset nest in item
	def reset_itemNests(self, table_name, itemList = []):
		"""
			Wrapper for unlocking nested tasks 
				itemList = [
					{'itemID': 'someID', 'TaskScript': [ 'Task_0' , 'Task_N']}
				]
		"""

		# Handle inputs
		if table_name is None or type(itemList) != list:
			print('Error, please provide table_name, item as a list, or taskKey or allTasks')

		# Handle items as a list
		elif type(itemList) is list:

			# Verify first item
			if type(itemList[0]) is dict:
				out = []
				for itemDict in itemList:
					itemID = itemDict['itemID']
					tasks = itemDict['TaskScript']					

					# Handle taskScript as dict
					if type(tasks) is dict:

						# Set the itemIDs taskScript.task.Status = todo
						for task in tasks.keys():
							logging = self.updateNestedItemState(table_name = table_name, itemID = itemID, taskKey = task)
							out.append(logging)

					# Otherwise reset string
					else:
						logging = self.updateNestedItemState(table_name = table_name, itemID = itemID, taskKey = tasks)
						out.append(logging)


			# Otherwise log error
			else:
				out = 'Error, invalid format please provide items as a list of tuples (itemID, [tasks]) or list of itemIDs and DO NOT UPDATE allTasks = 1'

		# Otherwise report error
		else:
			out = str('Error, not enough arguments supplied')

		# Return out
		return(out)


	# Reset all nested tasks for item
	def reset_AllNests(self, table_name, itemList = []):
		"""
			Unlock all nested items in the provide list of itemIDs
		"""

		# Handle arguments
		if type(itemList) != list:
			print('Provide a list items where all of their nested tasks are to be reset')

		# Otherwise proceed
		else:

			# Iteratively reset items
			out = []
			self.handle_DynamoTable(table_name)
			for itemID in itemList:

				# Try get & reset task script keys
				try:
					response = self.dynamo_table.query(
						ProjectionExpression = "itemID, TaskScript",
						ExpressionAttributeNames = { "#itemID": "itemID" },
						ExpressionAttributeValues = { ":itemKey": itemID },
						KeyConditionExpression = '#itemID = :itemKey'
					)
					tasks = list(response['Items'][0]['TaskScript'].keys())
					logging = [ self.updateNestedItemState(table_name = table_name, itemID = itemID, taskKey = task) for task in tasks ]

				# Log error for itemID
				except:
					logging = 'Error'

				# Append item logging
				out.append({itemID: logging})

			# Return out
			return(out)


	# Delete item
	def delete_singleItem(self, table_name, item = None):
		"""
			Delete an itemID or list of itemIDs
		"""

		# Handle item as string
		self.handle_DynamoTable(table_name)
		if item is not None and type(item) != list:
			try:
				response = self.dynamo_table.delete_item(Key = {'itemID': str(item)} )

			except:
				response = str('Error passing a single item must be a string')

		# Otherwise delete list
		else:

			# Test deleting first item
			itemID = item.pop(0)
			try:
				response = self.dynamo_table.delete_item(Key = {'itemID': str(itemID)})
				itemDeleted = 1

			except:
				itemDeleted = 0

			# Proceed with list if test was successful
			if itemDeleted == 1:
				response = [ self.dynamo_table.delete_item(Key = {'itemID': str(itemID)}) for itemID in item ]
			else:
				response = str('Error deleting item collection, must be a list. itemID = ' + itemID)

		# Return response
		return(response)


	# Delete nested tasks in item
	def delete_nestedTasks(self, table_name, itemID, taskKey = []):
		"""
			Delete the string / list of TaskScript keys for the supplied itemID.
			!!!! WARNING: ALL TASK SCRIPT KEYS WILL BE DELETED IF LIST IS EMPTY :) !!!!
		"""

		# Handle deleting all tasks in item
		self.handle_DynamoTable(table_name)
		if taskKey == []:

			# Get task script keys
			out = []
			response = self.dynamo_table.query(
				ProjectionExpression = "itemID, TaskScript",
				ExpressionAttributeNames = { "#itemID": "itemID" },
				ExpressionAttributeValues = { ":itemKey": itemID },
				KeyConditionExpression = '#itemID = :itemKey'
			)
			tasks = list(response['Items'][0]['TaskScript'].keys())


			# Remove all tasks
			for task in tasks:
				response = self.dynamo_table.update_item(
					Key = {'itemID': str(itemID)},
					ExpressionAttributeNames = {
						"#taskScript": 'TaskScript',
						"#task": str(task)
					},
					UpdateExpression = "REMOVE #taskScript.#task"
				)
				out.append(str('Deleted task = ' + task + ' from itemID = ' + itemID))


		# Otherwise iteratively clear taskKeys
		elif type(taskKey) is list:
			out = []
			for task in taskKey:
				response = self.dynamo_table.update_item(
					Key = {'itemID': str(itemID)},
					ExpressionAttributeNames = {
						"#taskScript": 'TaskScript',
						"#task": str(task)
					},
					UpdateExpression = "REMOVE #taskScript.#task"
				)
				out.append(str('Deleted task = ' + task + ' from itemID = ' + itemID))

		# Otherwise clear the string
		else:
			try:
				response = self.dynamo_table.update_item(
					Key = {'itemID': str(itemID)},
					ExpressionAttributeNames = {
						"#taskScript": 'TaskScript',
						"#task": str(taskKey)
					},
					UpdateExpression = "REMOVE #taskScript.#task"
				)
				out = str('Deleted task = ' + taskKey + ' from itemID = ' + itemID)

			# Log error
			except:
				out = str('Error taskKey must either be None, list or a string')

		# Log out
		return(out)


	# Clear nested tasks
	def clear_nestedTasks(self, table_name, itemList = []):

		# Handle arguments
		if type(itemList) != list:
			print('Provide a list items where all of their nested tasks are to be deleted')

		# Otherwise treat input as list of strings
		elif type(itemList[0]) != dict:

			# Iteratively reset items
			out = []
			self.handle_DynamoTable(table_name)
			for itemID in itemList:

				# Try delete all task script keys
				try:
					logging = self.delete_nestedTasks(table_name, itemID, taskKey = [])

				# Log error for itemID
				except:
					logging = 'Error'

				# Append item logging
				out.append({itemID: logging})

		# Otherwise treat inupt as dictionary
		else:
			out = []
			self.handle_DynamoTable(table_name)
			for item in itemList:
				itemID = item['itemID']
				tasks = item['TaskScript']

				# Delete all task script keys
				logging = self.delete_nestedTasks(table_name, itemID, taskKey = tasks)

				# Append item logging
				out.append({itemID: logging})

			# Return out
			return(out)

	# Summarize nested task progress
	def summarize_nestedTasks(self, table_name, output_results = 0):
		"""
			Summarize the progress of nested tasks in the form of
			output = {
				'0% ie todo': { 'N': int, 'Items': [ list of itemIDs ] },
				'1-24%': { 'N': int, 'Items': [ ] },
				'25-49%': { 'N': int, 'Items': [ ] },
				'50-74%': { 'N': int, 'Items': [ ] },
				'75-99%': { 'N': int, 'Items': [ ] },
				'100% ie done': { 'N': int, 'Items': [ ] }
			}
		"""

		# Summarize nested tasks
		self.handle_DynamoTable(table_name)
		nested_task_summary = {
			'todo': { 'N': 0, 'Items': [] },
			'Q1': { 'N': 0, 'Items': [] },
			'Q2': { 'N': 0, 'Items': [] },
			'Q3': { 'N': 0, 'Items': [] },
			'Q4': { 'N': 0, 'Items': [] },
			'done': { 'N': 0, 'Items': [] }
		}

		# Populate todo, done (PyAnamo-Engine client to)
		for itemState in [ 'todo', 'done' ]:
			itemStateData = self.getToDoItems(itemState, recursively = 0, pyanamo_fields = None)
			nested_task_summary[itemState]['N'] = itemStateData['N']
			nested_task_summary[itemState]['Items'] = itemStateData['Items']
			print( str('Item State = ' + itemState + ' N = ' + str(nested_task_summary[itemState]['N'])) )


		# Get locked items (PyAnamo-Engine client)
		lockedItems = self.getToDoItems('locked', recursively = 0, pyanamo_fields = 'itemID, TaskID, Nested_Tasks, Log_Length, TaskScript, Log, ItemState')


		# Analyze results: Q1 = 1-25%, Q2 = 26-50%, Q3 = 51-75%, Q4 = 75-99%
		print('\n\nChecking the progress of the locked items, N = ' + str(int(lockedItems['N'])) + '\n')
		for N in range(0, int(lockedItems['N'])):
			itemDict = lockedItems['Items'].pop(0)
			pct_progress = int(float(int(itemDict['Log_Length']) / int(itemDict['Nested_Tasks'])) * 100)
			if pct_progress == 0:
				nested_task_summary['todo']['N'] += 1
				nested_task_summary['todo']['Items'].append(str(itemDict['itemID']))

			elif pct_progress >= 1 and pct_progress <= 25:
				nested_task_summary['Q1']['N'] += 1
				nested_task_summary['Q1']['Items'].append(str(itemDict['itemID']))

			elif pct_progress > 25 and pct_progress <= 50:
				nested_task_summary['Q2']['N'] += 1
				nested_task_summary['Q2']['Items'].append(str(itemDict['itemID']))

			elif pct_progress > 50 and pct_progress <= 75:
				nested_task_summary['Q3']['N'] += 1
				nested_task_summary['Q3']['Items'].append(str(itemDict['itemID']))

			elif pct_progress > 75 and pct_progress <= 99:
				nested_task_summary['Q4']['N'] += 1
				nested_task_summary['Q4']['Items'].append(str(itemDict['itemID']))

			elif pct_progress == 100:
				nested_task_summary['done']['N'] += 1
				nested_task_summary['done']['Items'].append(str(itemDict['itemID']))

		# Print summary
		for taskQ in nested_task_summary.keys():
			print(str(taskQ + ' = ' + str(nested_task_summary[taskQ]['N'])))

		# Return dictionary
		if output_results == 1:
			return(nested_task_summary)


	# Monitor nested tasks
	def monitor_nestedTasks(self, table_name, Niterations = 1, waitTime = 0):
		"""
			Monitor the nested task summary over time
		"""

		# Run item counter for N iterations, with wait time between them		
		N = 0
		taskSummary = {}
		while N < Niterations:

			# Get item IDs per state
			N += 1
			iterID = str("Iteration_" + str(N))
			itemSummary = self.summarize_nestedTasks(table_name, output_results = 1)

			# Clear items from reults
			for summaryKey in itemSummary.keys():
				del itemSummary[summaryKey]['Items']

			# Append active iteration
			taskSummary.update( {iterID: itemSummary} )
			time.sleep(int(waitTime))

		# Return taskSummary
		return(taskSummary)


	# Get job states for items
	def getItem_JobStates(self, table_name):
		"""
			Map locked items to their AWS-Batch job states
			output = {
				'SUCCEEDED': [],
				'FAILED': [],
				'RUNNING': [],
				'OTHER': [],
				'ERROR_FETCHING': []
			}
		"""

		# Query instanceIDs of locked tasks
		self.handle_DynamoTable(table_name)
		batch_client = boto3.client('batch')
		lockedItems = self.dynamo_table.query(
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


		# Check batch job state of lockedItems
		itemJobStates = {'SUCCEEDED': [], 'FAILED': [], 'RUNNING': [], 'OTHER': [], 'ERROR_FETCHING': [] }
		for task in lockedItems:
			jobID = '-'.join(task['InstanceID'].split('-')[0:-1])
			jobID = str(jobID + ':' + task['InstanceID'].split('-')[-1])
			try:
				response = batch_client.describe_jobs(jobs = [jobID])['jobs'][0]
			except:
				response = {'status': 'ERROR_FETCHING'}

			# Handle where to store item
			if response['status'] == 'SUCCEEDED' or response['status'] == 'FAILED' or response['status'] == 'RUNNING' or response['status'] == 'ERROR_FETCHING':
				jobState = response['status']
				itemJobStates[jobState].append(str(task['itemID']))

			# Append to other is state is unknown
			else:
				jobState = response['status']
				itemJobStates['OTHER'].append(str(jobState + "_Item_" + str(task['itemID'])))

		# Return results
		return(itemJobStates)


	# Set hard provisioning for read/write
	def set_hardProvision(self, table_name, writeCapacity, readCapacity):
		"""
			Set custom Read and Write Capacity units of some workflow table by their name
		"""

		# Hard provision of table with supplied capacities
		self.handle_DynamoTable(table_name)
		dynamodb_client = boto3.client('dynamodb')
		basTableProvisioning = {'ReadCapacityUnits': int(readCapacity), 'WriteCapacityUnits': int(writeCapacity)}
		GSI_Provisioning = { "GlobalSecondaryIndexUpdates": [
			{ 'Update': { 'IndexName': 'ItemStateIndex','ProvisionedThroughput': { 'ReadCapacityUnits': int(readCapacity), 'WriteCapacityUnits': int(writeCapacity) }} },
			{ 'Update': { 'IndexName': 'TaskStateIndex','ProvisionedThroughput': { 'ReadCapacityUnits': int(readCapacity), 'WriteCapacityUnits': int(writeCapacity) }} },
			{ 'Update': { 'IndexName': 'InstanceStateIndex','ProvisionedThroughput': { 'ReadCapacityUnits': int(readCapacity), 'WriteCapacityUnits': int(writeCapacity) }} },
			{ 'Update': { 'IndexName': 'LoggingIndex','ProvisionedThroughput': { 'ReadCapacityUnits': int(readCapacity), 'WriteCapacityUnits': int(writeCapacity) }} }
			]
		}

		# Apply provisioning
		try:
			response = dynamodb_client.update_table(
				TableName = table_name,
				ProvisionedThroughput = basTableProvisioning,
				GlobalSecondaryIndexUpdates = GSI_Provisioning['GlobalSecondaryIndexUpdates']
			)
			time.sleep(int(10))
			out = response['TableDescription']
		except dynamodb_client.exceptions.ClientError as dynamoError:
			print('Error setting the provisioning of the requested table. See DynamoDB error in output')
			out = dynamoError

		# Return output
		return(out)

	# Set autoscaling target
	def setAutoScalingTarget(self, table_name, writeCapacity, readCapacity):
		"""
			Set the auto-scaling targets of the table + GSI
			!!!! WARNING: ONLY NEEDS TO BE DONE ONCE PER TABLE !!!
		"""

		# Set auto-scaling provision values: Table and GSI
		capacityData = {'WriteCapacity': int(writeCapacity), 'ReadCapacity': int(readCapacity)}
		table_scaling = [
			( str('table/' + table_name), 'dynamodb:table' ),
			( str('table/' + table_name + '/index/' + "ItemStateIndex"), 'dynamodb:index'),
			( str('table/' + table_name + '/index/' + "TaskStateIndex"), 'dynamodb:index'),
			( str('table/' + table_name + '/index/' + "InstanceStateIndex"), 'dynamodb:index'),
			( str('table/' + table_name + '/index/' + "LoggingIndex"), 'dynamodb:index')
		]

		# Register a scalable target with min and max bound for Read + Write
		autoscaling_client = boto3.client('application-autoscaling')
		out = {
			'ScalableTarget': {
				'Read_Capacity': {'Success': [] , 'Failed': [] },
				'Write_Capacity': {'Success': [] , 'Failed': [] }
			}
		}

		# Register the read and then the write capacity
		for scaleComponent in table_scaling:
			scale_resourceID = scaleComponent[0]
			scale_Dimension = scaleComponent[1]

			try:
				response = autoscaling_client.register_scalable_target(
					ServiceNamespace = 'dynamodb',
					ResourceId = scale_resourceID,
					ScalableDimension = str(scale_Dimension + ':ReadCapacityUnits'),
					MinCapacity = 1,
					MaxCapacity = capacityData['ReadCapacity'],
					SuspendedState = { 'DynamicScalingInSuspended': False, 'DynamicScalingOutSuspended': False, 'ScheduledScalingSuspended': False  }
				)
				out['ScalableTarget']['Read_Capacity']['Success'].append(str(scale_resourceID + ' ' + scale_Dimension))
			except:
				out['ScalableTarget']['Read_Capacity']['Failed'].append(str(scale_resourceID + ' ' + scale_Dimension))

			# Register write capacity
			try:
				response = autoscaling_client.register_scalable_target(
					ServiceNamespace = 'dynamodb',
					ResourceId = scale_resourceID,
					ScalableDimension = str(scale_Dimension + ':WriteCapacityUnits'),
					MinCapacity = 1,
					MaxCapacity = capacityData['WriteCapacity'],
					SuspendedState = { 'DynamicScalingInSuspended': False, 'DynamicScalingOutSuspended': False, 'ScheduledScalingSuspended': False  }
					)
				out['ScalableTarget']['Write_Capacity']['Success'].append(str(scale_resourceID + ' ' + scale_Dimension))
			except:
				out['ScalableTarget']['Write_Capacity']['Success'].append(str(scale_resourceID + ' ' + scale_Dimension))

		# Wait and return out
		time.sleep(int(10))
		return(out)


	# Put scaling policies on table + GSI
	def putScalingPolicy(self, table_name, target_Value, scaleDown, scaleUp):
		"""
			Apply desired auto-scaling to table + GSI
		"""

		# Put scaling policy output template
		[ int(scaleUp), int(scaleDown), float(target_Value) ]
		autoscaling_client = boto3.client('application-autoscaling')
		out = { 
			'Put_Policy': {
				'Read_Capacity': {'Success': [] , 'Failed': [] },
				'Write_Capacity': {'Success': [] , 'Failed': [] }
			}
		}

		# Policies to add Read and Write for
		table_scaling = [
			( str('table/' + table_name), 'dynamodb:table' ),
			( str('table/' + table_name + '/index/' + "ItemStateIndex"), 'dynamodb:index'),
			( str('table/' + table_name + '/index/' + "TaskStateIndex"), 'dynamodb:index'),
			( str('table/' + table_name + '/index/' + "InstanceStateIndex"), 'dynamodb:index'),
			( str('table/' + table_name + '/index/' + "LoggingIndex"), 'dynamodb:index')
		]


		# Read then write, table then indexes
		for scaling_component in table_scaling:
			scaling_resourceID = scaling_component[0]
			scaling_Dimension = scaling_component[1]
			scaling_PolicyName = str(table_name + '_' + scaling_resourceID.split('/')[-1]).replace(table_name + '_' + table_name, table_name)

			# Write capacity 
			try:
				response = autoscaling_client.put_scaling_policy(
    				PolicyName = str(scaling_PolicyName + '_Write_Capacity_Scaling'),
    				ServiceNamespace = 'dynamodb',
    				ResourceId = scaling_resourceID,
    				ScalableDimension = str(scaling_Dimension + ':WriteCapacityUnits'),
    				PolicyType = 'TargetTrackingScaling',
					TargetTrackingScalingPolicyConfiguration = {
						'PredefinedMetricSpecification': { 'PredefinedMetricType': 'DynamoDBWriteCapacityUtilization' },
						'ScaleOutCooldown': int(scaleUp),
						'ScaleInCooldown': int(scaleDown),
						'TargetValue': float(target_Value)
					}
				)
				out['Put_Policy']['Write_Capacity']['Success'].append(response['PolicyARN'])
			except:
				out['Put_Policy']['Write_Capacity']['Failed'].append(scaling_PolicyName)

			# Read capacity
			try:
				response = autoscaling_client.put_scaling_policy(
    				PolicyName = str(scaling_PolicyName + '_Read_Capacity_Scaling'),
    				ServiceNamespace = 'dynamodb',
    				ResourceId = scaling_resourceID,
    				ScalableDimension = str(scaling_Dimension + ':ReadCapacityUnits'),
    				PolicyType = 'TargetTrackingScaling',
					TargetTrackingScalingPolicyConfiguration = {
						'PredefinedMetricSpecification': { 'PredefinedMetricType': 'DynamoDBReadCapacityUtilization' },
						'ScaleOutCooldown': int(scaleUp),
						'ScaleInCooldown': int(scaleDown),
						'TargetValue': float(target_Value)
					}
					)
				out['Put_Policy']['Read_Capacity']['Success'].append(response['PolicyARN'])
			except:
				out['Put_Policy']['Read_Capacity']['Failed'].append(scaling_PolicyName)

		# Return output
		time.sleep(int(10))
		return(out)
