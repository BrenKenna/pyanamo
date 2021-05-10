################################
################################
# 
# Client Class:
# 
#################################
#################################


# Test out
python
import boto3
from client import PyAnamo_Client


# Make table object
dynamodb = boto3.resource('dynamodb', region_name = 'us-east-1')
table = dynamodb.Table('Testing')
pyanamoClient = PyAnamo_Client(table)


# Item counter
data = pyanamoClient.itemCounter(table)


# Query item state and lockID
itemState = pyanamoClient.getCurrentState(0)
itemLockID = pyanamoClient.getLockID(0)


# Get todo items
itemState = 'todo'
todoItems = pyanamoClient.getToDoItems(itemState, pyanamo_fields = 'itemID, taskID, lockID, instanceID, ItemState, Log, Log_Length, TaskScript')


# Get locked items
itemState = 'locked'
lockedItems = pyanamoClient.getToDoItems(itemState, pyanamo_fields = 'itemID, taskID, lockID, instanceID, ItemState, Log_Length, lockID, Locked_Date, Log, TaskScript', recursively = 1)
lockedItems['Items'][0]['lockID']


# Get done items
itemState = 'done'
doneItems = pyanamoClient.getToDoItems(itemState, pyanamo_fields = 'itemID, taskID, lockID, instanceID, ItemState, Log_Length, lockID, Locked_Date, Log, Done_Date, Nested_Tasks')

