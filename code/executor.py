#!/usr/bin/python


# Import modules
import boto3, string, re, os, time, sys, json, gzip
from subprocess import Popen, PIPE
from datetime import datetime
import client as pc
import modifier as pm


# Initialize s3 & cloudwatch clients
s3_client = boto3.client('s3')
cloudwatch_client = boto3.client('logs')


# Exit if environmental variables are not defined
try:
	pyanamo = os.environ['PYANAMO']

except KeyError:
	print("\n\nExiting, global variable for PYANAMO not found")


# Class to manage the execution of task scripts
class PyAnamo_Executor(pm.PyAnamo_Modifier):

	"""
		Class to manage the execution of items supplied by the PyAnamo_Runner & Directing logs to DynamoDB, CloudWatch or S3.
		Task log direction is separate out for Nested and Un-nested items
	"""

	# Initialize
	def __init__(self, dynamo_table, itemDict = None):

		# Also include: instanceID, s3Bucket
		if itemDict is not None:
			self.itemDict = itemDict

		# Dynamo table
		if dynamo_table is not None:
			self.dynamo_table = dynamo_table
			self.pyanamoClient = pc.PyAnamo_Client(self.dynamo_table, region = dynamo_table.table_arn.split(':')[3])
			self.pyanamoModifier = pm.PyAnamo_Modifier(self.dynamo_table)


	# Execute & parse taskScript log
	def executeTaskScript(self, taskScript):

		"""
			Execute the supplied task script as a string.
			Requires the script to be stored in folder referenced by PYANAMO environmental variable.
			Returns a One or Zero (int) depending on subprocess.OSError and the task log
			taskLog = {Date: 'HH:MM:SS-DD/MM/YYYY', Log: { stderr: "". stdout: "", Status: ""} }
		"""

		# Initialize output dict
		taskLog = {
			"Done_Date": "",
			"Log": {
				"Status": "",
				"stdout": "",
				"stderr": ""
			},
			"Log_Length": ""
		}

		# Try execute input
		try:

			# Execute and parse logs
			taskScript = taskScript.replace("${PYANAMO}", pyanamo)
			proc = Popen(taskScript.split(" "), stdout = PIPE, stderr = PIPE)
			stdout, stderr = proc.communicate()
			stdout = stdout.decode('utf-8')
			stderr = stderr.decode('utf-8')
			log_length = len(stdout.split("\n"))
			now = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")

			# Update output dict
			taskLog["Done_Date"] = str(now)
			taskLog["Log"]["Status"] = str("Execution Successful")
			taskLog["Log"]["stdout"] = str(stdout)
			taskLog["Log"]["stderr"] = str(stderr)
			taskLog["Log_Length"] = int(log_length)
			taskDone = 1

		# Handle execution error
		except OSError:
			now = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
			taskLog["Done_Date"] = str(now)
			taskLog["Log"]["Status"] = str("Execution Failed")
			taskDone = 0

		return(taskDone, taskLog)


	# Parse out PyAnamo tags
	def parsePyanamoTags(self, log):

		"""
			Parses out any lines in the task Log containing 'PyAnamo:'
				-> Method is implemented to salavage information from big logs for DynamoDB
		"""

		pattern = re.compile("PyAnamo:\t")
		log = list(filter(None, log.split('\n')))
		log = "\n".join(list(filter(pattern.match, log)))
		log = log.replace("PyAnamo:\t", "")
		return(log)


	# Compress input to s3
	def compresedPushS3(self, content, out, s3Bucket, s3BucketKey):

		"""
			GZIP compresses input content to an out file and pushes to the s3Buckets path / s3BucketKey
		"""

		# Compress input content
		content = bytes(content, 'utf-8')
		with gzip.open(out, 'wb') as f:
			f.write(content)

		# Push file to s3 and remove
		response = s3_client.upload_file(out, s3Bucket, s3BucketKey)
		os.remove(out)
		return("Compressed to S3 " + str("s3://" + s3Bucket + "/" + s3BucketKey))


	# Handle push / updating log streams
	def cloudWatchPush(self, taskMessage, logGroup, logStream):

		"""
			Creates or updates Cloudwatch stream for the active task
			Format = /PyAnamo/PYANAMO_TABLE/INSTANCE_ID or AWS-Batch-ID/taskID
		"""

		# Create log group if none
		response = cloudwatch_client.describe_log_groups(logGroupNamePrefix = logGroup)
		if len(response["logGroups"]) == 0:
			response = cloudwatch_client.create_log_group(logGroupName = logStream)

		# Handle updating / creating the log stream
		response = cloudwatch_client.describe_log_streams(logGroupName = logGroup, logStreamNamePrefix = logStream)
		if len(response["logStreams"]) == 0:

			# Create log stream
			response = cloudwatch_client.create_log_stream(logGroupName = logGroup, logStreamName = logStream)
			response = cloudwatch_client.put_log_events(logGroupName = logGroup, logStreamName = logStream, logEvents = taskMessage)
			return("Created Cloudwatch " + logGroup + logStream)

		else:

			# Otherwise update
			nextSequenceToken = response["logStreams"][0]["uploadSequenceToken"]
			response = cloudwatch_client.put_log_events(logGroupName = logGroup, logStreamName = logStream, sequenceToken = nextSequenceToken, logEvents = taskMessage)
			return("Updated Cloudwatch " + logGroup + logStream)


	# Handle logs
	def handleLogs(self, log, table_name, instanceID, taskID, s3Bucket):

		"""
			Determine where to put the task log.
			<2KB = DynamoDB
			2KB - 100KB = Cloudwatch
			>100KB = S3
		"""

		# Update dynamo if < 2KB
		logSize = sys.getsizeof(log)
		if logSize < 2000:
			return(["0", "DynamoDB"])

		# Direct to cloudwatch if 2KB -> 10MB
		elif logSize > 2000 and logSize < 100000:

			# Parse out PyAnamo tags + Cloud watch push
			pyAnamoTags = self.parsePyanamoTags(log)
			logGroup = "/PyAnamo/"
			taskID = re.sub('_Task_[0-9]*', '', taskID)
			logStream = str(table_name + "/" + instanceID + "/" + taskID)
			taskMessage = [
				{
					"timestamp": int(round(time.time() * 1000)),
					"message": str("\n" + log + "\n")
				}
			]
			response = self.cloudWatchPush(taskMessage, logGroup, logStream)

			# Evaluate tags size
			if sys.getsizeof(pyAnamoTags) > 2000:
				pyAnamoTags = response
			return(["1", response, pyAnamoTags])

		# Otherwise write to a compressed file and push to s3: 	Parse for PyAnamo tag if <900MB
		else:

			# Compress to S3 file
			out = str(taskID + '.TaskLog.txt.gz')
			s3BucketKey = str("PyAnamo/" + table_name + "/" + out)
			out = self.compresedPushS3(log, out, s3Bucket, s3BucketKey)
			return(["1", out, out])


	# Manage log push
	def taskLogDirector(self, taskDone, taskLog, table_name, instanceID, s3Bucket, taskData):

		"""
			Executes the task log handler and pushes filtered task log to DynamoDB
		"""

		# Handle logs: Maybe just give the updateItem function the data object to handle
		itemID = str(taskData['itemID'])
		taskID = taskData['taskID']
		data = self.handleLogs(taskLog["Log"]["stdout"] + taskLog["Log"]["stderr"], table_name, instanceID, taskID, s3Bucket)

		# Update Dynamo according to the Log Handler
		if data[0] == "0":

			# Push the unmodified taskLog
			print(str("\nUpdating Dynamo without taskLog modification"))
			self.updateItemLog(taskDone, itemID, taskLog)

		# Otherwise push the modified log
		elif data[0] == "1":
			print(str("\nUpdating Dynamo with taskLog modification"))
			taskLog["Log"]["Status"] = str("Execution Successful: " + data[1])
			taskLog["Log"]["stdout"] = data[2]
			taskLog["Log"]["stderr"] = ""

			self.updateItemLog(taskDone, itemID, taskLog)

		else:
			print(str("\nError updating DynamoDB, no route to Cloudwatch or S3 could be resolved"))


	# Manage log push for nested tasks
	def Nested_taskLogDirector(self, taskDone, table_name, instanceID, s3Bucket, nested_Data):

		"""
			A taskLogDirector() for Nested Task Items
		"""

		# Handle logs: Maybe just give the updateItem function the data object to handle
		itemID = str(nested_Data['itemID'])
		taskID = nested_Data['taskID']
		del nested_Data['itemID'], nested_Data['taskID']
		nestedID = nested_Data['nestedID']
		taskLog = nested_Data[nestedID]['Log']
		log_length = nested_Data['Log_Length']
		taskScript = nested_Data[nestedID]['TaskScript']
		data = self.handleLogs(taskLog["stdout"] + taskLog["stderr"], table_name, instanceID, taskID, s3Bucket)

		# Update Dynamo according to the Log Handler
		if data[0] == "0":

			# Push the unmodified taskLog
			print(str("\nUpdating Dynamo without taskLog modification"))
			self.updateNestedItem(itemID, itemImport = nested_Data)


		# Otherwise push the modified log
		elif data[0] == "1":
			print(str("\nUpdating Dynamo with taskLog modification"))
			taskLog["Status"] = str("Execution Successful: " + data[1])
			taskLog["stdout"] = data[2]
			taskLog["stderr"] = ""
			nested_Data[nestedID]['Log'] = taskLog
			self.updateNestedItem(itemID, itemImport = nested_Data)

		else:
			print(str("\nError updating DynamoDB, no route to Cloudwatch or S3 could be resolved"))
