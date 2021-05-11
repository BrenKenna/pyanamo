#!/usr/bin/python


# Import modules
import boto3, random
from boto3.dynamodb.conditions import Key, Attr


# Class to interact with a Dynamo table object
class PyAnamo_Client():

	"""
		Class to manage interating with the supplied Dynamo Client.
		The PyAnamo_Client includes methods to:
			- Recursively query/scan items from Dynamo Table.
			- Get all todoItems for the PyAnamo_Runner to iterate over
			- Get and count all items for the; todo, locked AND done states.
			- Get attributes of the given task; Item State, InstanceID.
			- Put and Update items (Querky behavior when passed keyword arguments)
	"""

	# Initialize object
	def __init__(self, dynamo_table, region):

		# Dynamo
		if type(dynamo_table) is str:
			self.dynamodb = boto3.resource('dynamodb', region_name = region)
			self.dynamo_table = self.dynamodb.Table(dynamo_tableName)

		elif type(dynamo_table) is not str:
			self.dynamo_table = dynamo_table

	# Recursive get data (scan or query)
	def recursiveGet(self, dynamo_table, dynamoGet_kwargs, dynamoGetMethod):

		"""
			Recursively query or scan the dynamoDB table for the supplied keyword arguments
		"""

		# Handle scan / query
		if dynamoGetMethod == 'scan':

			# Scan table
			response = dynamo_table.scan(**dynamoGet_kwargs)
			data = response['Items']

			# Keep scanning until all data is fethed
			while 'LastEvaluatedKey' in response:
			    response = dynamo_table.scan(ExclusiveStartKey = response['LastEvaluatedKey'])
			    data.extend(response['Items'])


		# Otherwise query
		elif dynamoGetMethod == 'query':

			# Query table
			response = dynamo_table.query(**dynamoGet_kwargs)
			data = response['Items']

			# Keep scanning until all data is fethed
			while 'LastEvaluatedKey' in response:
			    response = dynamo_table.query(ExclusiveStartKey = response['LastEvaluatedKey'], **dynamoGet_kwargs)
			    data.extend(response['Items'])


		# Handle error
		else:
			data = 'Error, scan or query'

		return(data)


	# Get items by state
	def getToDoItems(self, itemState, recursively = 1, pyanamo_fields = None):

		"""
			Get the PyAnamo fields for the supplied item state.
			Default is recursively, requires proper provisioning of the table in question
		"""

		# Initialize the ouput dictionary
		itemDict = { "ItemState": itemState, "N": 0, "Items": [] }

		# Handle pyanamo fields: Item ID
		if pyanamo_fields == None:
			pyanamo_fields = "itemID"

		# Otherwise replace key words
		else:
			pyanamo_fields = ", ".join(set([ i.replace(i, '#taskLog') if i == 'Log' else i for i in pyanamo_fields.replace(' ', '').split(',') ]))


		# Template query
		query_kwargs = {
			"IndexName" : "ItemStateIndex",
			"ProjectionExpression": pyanamo_fields,
			"ExpressionAttributeNames": { "#itemstate": "ItemState", "#taskLog": 'Log' },
			"ExpressionAttributeValues": { ":state": itemState },
			"KeyConditionExpression": '#itemstate = :state'
		}


		# Run query
		if recursively == 1:
			response = self.recursiveGet(self.dynamo_table, query_kwargs, 'query')

		else:
			response = self.recursiveGet(self.dynamo_table, query_kwargs, 'query')


		# Parse results and return the dictionary
		itemDict["Items"] = response
		random.shuffle(itemDict["Items"])
		itemDict["N"] = len(itemDict["Items"])
		return(itemDict)


	# Get an items current state
	def getCurrentState(self, itemID, recursively = 1):
		"""
			Get the current state of the supplied item
		"""

		# Set query args
		query_kwargs = {
			"ProjectionExpression": "ItemState",
			"ExpressionAttributeNames": { "#itemID": "itemID" },
			"ExpressionAttributeValues": { ":itemKey": itemID },
			"KeyConditionExpression": '#itemID = :itemKey'
		}

		# Query the ItemState for itemID
		if recursively == 1:
			currentState = self.recursiveGet(self.dynamo_table, query_kwargs, 'query')[0]

		else:
			response = self.recursiveGet(self.dynamo_table, query_kwargs, 'query')[0]

		return(currentState)


	# Get lockID of item
	def getLockID(self, itemID, recursively = 1):
		"""
			Get the lockID of the supplied item
			Used by the PyAnamo_Modifier for itemVerification method
		"""

		# Set query args
		query_kwargs = {
			"ProjectionExpression": "lockID",
			"ExpressionAttributeNames": { "#itemID": "itemID" },
			"ExpressionAttributeValues": { ":itemKey": itemID },
			"KeyConditionExpression": '#itemID = :itemKey'
		}

		# Query the lockID for item
		if recursively == 1:
			currentState = self.recursiveGet(self.dynamo_table, query_kwargs, 'query')[0]

		else:
			currentState = self.recursiveGet(self.dynamo_table, query_kwargs, 'query')[0]
		
		return(currentState)


	# Item counter
	def itemCounter(self, dynamo_table, return_all = 1):

		"""
			Get all of the items from each state and count of all items
			Results stored in a dictionary
		"""

		# Template output dict
		itemData = { 'todo': [], 'locked': [ ], 'done': []}
		for itemState in itemData.keys():

			# Set query args
			query_kwargs = {
				"IndexName": 'ItemStateIndex',
				"ProjectionExpression": "itemID, ItemState",
				"ExpressionAttributeNames": { "#lockID": "ItemState" },
				"ExpressionAttributeValues": { ":lockKey": str(itemState) },
				"KeyConditionExpression": '#lockID = :lockKey'
			}
			data = self.recursiveGet(self.dynamo_table, query_kwargs, 'query')
			itemData[itemState].extend(data)

		# Count the number of values in each key
		itemData['ItemCount'] = sum([ len(itemData[i]) for i in itemData.keys() ])		

		# Return item count if specified
		if return_all == 0:
			return(itemData['ItemCount'])

		# Otherwise return full dict
		else:
			return(itemData)
