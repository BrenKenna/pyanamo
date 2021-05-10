############################
############################
# 
# Executor Class
# 
############################
############################


# Test out
python
import boto3, executor
from ec2_metadata import ec2_metadata


# Create an itemDict
taskID = str('Task-11')
itemID = int(43)
s3Bucket = 'herp_a_derp'
instanceID = ec2_metadata.instance_id
taskScript = "bash ${PYANAMO}/mega-test.sh"
itemDict = {'Log': {}, 'taskID': 'Task-11', 'Log_Length': int('0'), 'TaskScript': {'Task_1': {'Status': 'todo', 'Script': 'seq 2'}, 'Task_0': {'Status': 'todo', 'Script': 'seq 11'}, 'Task_2': {'Status': 'todo', 'Script': 'seq 3'}}, 'itemID': int('43'), 'lockID': 'NULL', 'ItemState': 'todo'}


# Initialize executor
dynamodb = boto3.resource('dynamodb', region_name = 'us-east-1')
table = dynamodb.Table('Testing')
pyanamoExecutor = executor.PyAnamo_Executor(table, itemDict)


# Test functionalities
taskDone, taskLog = pyanamoExecutor.executeTaskScript(taskScript)
data = pyanamoExecutor.handleLogs(taskLog["Log"]["stdout"] + taskLog["Log"]["stderr"], 'Testing', instanceID, taskID, s3Bucket)


# Test proper function
pyanamoExecutor.taskLogDirector('0', taskLog, table, instanceID, s3Bucket, itemDict)

