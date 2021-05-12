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
			# Create / Remove workflow table (Manager)
			# Describe the workflow table schema (Manager)
			- Alter table provisioning and set auto-scaling (Manager)
			- Check whether specific items do or do not exist (Manager + Client-getCurrentState)
			- Import task, list or text file of tasks to table (Manager)
			- Summarize the PyAnamo item states (optionally over-time) (Manager + Client-itemCounter)
			- Change item states (optionally user-defined string (Manager + Client)
			- Retrieve item logs, instanceIDs (Manager + Client-getToDoItems)
			- Translate itemStates to AWS-Batch job states (Manager + Client)
			- Unlock / Restart tasks (Manager)
			- Unlock specific nested tasks within specific items (Manager)
			- Delete specific items (Manager)
			- Template for managing custom priority queue (itemStates + monitoring over time) (Manager + Client)
	"""

	# Initialize object
	def __init__(self, dynamo_table = None, region = None):

		# Dynamo
		if type(dynamo_table) is str:
			self.dynamodb = boto3.resource('dynamodb', region_name = region)

		elif type(dynamo_table) is not str:
			self.dynamo_table = dynamo_table


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
			{ 'AttributeName': "Log_Length", "AttributeType": "S" }
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
			table = self.dynamodb.Table(table_name)
			table.delete()
			time.sleep(int(10))
			out = int(1)
			print('Table = ' + table_name + ' deleted')

		# Otherwise log non-existent
		else:
			out = int(0)
			print('Table = ' + table_name + ' does not exist')
		return(out)
