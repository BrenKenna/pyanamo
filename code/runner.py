#!/usr/bin/python


# Import modules
import boto3, string, random, re, os, time, sys, json, gzip
from subprocess import Popen, PIPE
from datetime import datetime
import executor
import client as pc
import modifier as pm
import parallel_processes
import pyanamo_errors as perr
import timeKeeper as ptk


# Iterate over todo items: Import random, lockStreak as self.___
class PyAnamo_Runner(executor.PyAnamo_Executor):
	"""
		Class inheriting the PyAnamo_Client, PyAnamo_Modifier and PyAnamo_Executor methods.
		Purpose is to fetch a randomly sorted list of todo items from supplied Dynamo Client.
		A handler determine whether to process the item as Nested or Un-nested.
		The ouput of the modifiers itemVerification is used to manage updating the todo list after 3 cosecutive lock streaks
	"""

	# Initialize
	def __init__(self, dynamo_table, s3Bucket = None, Parallel_Nests = 0, aws_region = None, todoDict = None, timeLimit = None):
		super(PyAnamo_Runner, self)
		self.dynamo_table = dynamo_table
		self.table_name = dynamo_table.name
		self.Parallel_Nests = Parallel_Nests
		self.s3Bucket = s3Bucket
		self.aws_kwargs = {
				"region": aws_region,
				"s3_key": s3Bucket,
				"nested_parallel": Parallel_Nests,
				"dynamo_table": dynamo_table.name
			}
		self.lockStreak = 0
		self.instanceID = self.getInstanceID()
		self.timeLimit = timeLimit

		# Handle instantition outside of main process (nested item parallelization)
		if todoDict == None:
			self.todoDict = todoDict

		# Otherwise assume main process
		else:
			self.todoDict = self.getToDoItems('todo', pyanamo_fields = 'itemID, taskID, lockID, instanceID, ItemState, Log, Log_Length, TaskScript', recursively = 0)
			self.doneTasks = {
				"N": 0,
				"Items": [ ]
			}

		# Handle composing time keeper: Have validation as a function
		if self.timeLimit != None:
			self.timeKeeper = ptk.PyAnamo_TimeKeeper(timeLimit)


	# Handle processing un-nested / single task items: taskScript, todo_item
	def handleSingleTasks(self, todo_item):
		"""
			Process the input dictionary in single task mode.
			The purpose is to coordinate with the Executors taskLogDirector
		"""

		# Run the executor methods for executing tasks
		itemID = todo_item["itemID"]
		taskID = todo_item["taskID"]
		taskScript = todo_item["TaskScript"]
		taskDone, taskLog = self.executeTaskScript(taskScript)

		# Pass log to the executors log handler
		self.taskLogDirector(taskDone, taskLog, self.table_name, self.instanceID, self.s3Bucket, todo_item)
		print('\nExecution successful, updating status and logs for itemID = ' + str(itemID))


	# Handle processing nested items: todo_item, table_name, instanceID, s3Bucket
	def handleNestedItem(self, todo_item):
		"""
			Process the input dictionary in nested task mode.
			The purpose is to coordinate with the Executors Nested_taskLogDirector
		"""

		# Only process nested items that are todo
		itemID = todo_item["itemID"]
		taskID = todo_item["taskID"]
		taskScript = todo_item["TaskScript"]
		todo_item['Log_Length'] = 0


		# Iteratively process taskScripts: Make separate function to parallelize, since update is outside
		taskScriptKeys = list(taskScript.keys())
		random.shuffle(taskScriptKeys)
		while len(taskScriptKeys) != 0:

			# Skip if not todo
			taskKey = taskScriptKeys.pop(0)
			task = list(taskScript.keys())[taskKey]
			if taskScript[task]['Status'] != 'todo':
				print("\nSkipping task " + str(task) + "\n")
				todo_item['Log_Length'] += 1
				continue

			# Otherwise process the todo nested task
			print("\nProcessing nested task = " + str(task) + ' from item = ' + str(itemID))
			taskDone, taskLog = self.executeTaskScript(taskScript[task]["Script"])

			# Update data to pass to the PyAnamo Executor logDirector
			print('\nExecution successful, updating status and logs for itemID = ' + str(itemID))
			taskScript[task]['Status'] = "done"
			todo_item['Log_Length'] += 1
			nested_Data = {
				"itemID": str(itemID),
				"taskID": taskID,
				"nestedID": task,
				"Log_Length": todo_item["Log_Length"],
				task: { "TaskScript": taskScript[task], "Log": taskLog['Log'] }
			}
		
			# Pass the results to Executors nested task log director (Dynamo, Cloudwatch or S3)
			self.Nested_taskLogDirector(taskDone, self.table_name, self.instanceID, self.s3Bucket, nested_Data)

			# Consult PyAnamo Time Keeper if configured
			canRunNextTask = 1
			if 'timeKeeper' in self.__dict and self.timeKeeper != None:

				# Check wall times
				canRunNextTask = self.checkTime()

				# Break loop in not last task and cannot run next task
				if len(taskScriptKeys) != 0 and canRunNestTask == 0:
					print('Breaking Loop due to elapsing wall time')
					break

				# Handle last task
				elif len(taskScriptKeys) == 0:
					canRunNextTask = 1

		# Return
		return(canRunNextTask)


	# Process tasks in the todoDict: table_name, instanceID, s3Bucket: Run this function in parallel if PyAamo Threads >= 2 (random wait at start)
	def processItems(self):
		"""
			Conintually pop the first todo item from the list items.
			Verifiy that the active is still locked
			Pass the item to this Runners task handler
			Or update lock streak if locked
		"""

		# Pop first item until none left
		print("\nProcessing tasks from table = " + str(self.table_name))
		while len(self.todoDict['Items']) != 0:

			# Set convenient variables
			todo_item = self.todoDict['Items'].pop(0)
			itemID = todo_item["itemID"]
			taskID = todo_item["taskID"]
			taskScript = todo_item["TaskScript"]

			# Proceed with active item if still available
			print('\nAttempting to lock taskID = ' + taskID + " under itemID = " + str(itemID))
			itemVerified = self.verifyItem(itemID)
			if itemVerified == 1:

				# Determine how to process the active item: Nested vs Un-nested
				if type(taskScript) == dict:

					# Handle parallel processing
					if self.Parallel_Nests > 1:

						# Process the item as nested: 
						print("Parallel processing active task as nested item")
						parallel_processes.nestedItem_main(self.Parallel_Nests, aws_kwargs = self.aws_kwargs, nested_item = todo_item)
						self.updateNestedItem(itemID)
						print('\nExecution successful, updating itemID = ' + str(itemID) + ' as done')

					# Otherwise single processing
					else:

						# Process the item as nested
						print("Processing active task as nested item")
						self.handleNestedItem(todo_item)
						self.updateNestedItem(itemID)
						print('\nExecution successful, updating itemID = ' + str(itemID) + ' as done')

				# Otherwise process task as a single item
				else:

					# Process as a single task item
					print("Processing active task as single item")
					self.handleSingleTasks(todo_item)

					# Consult PyAnamo Time Keeper if next task can be taken
					canRunNextTask = 1
					if 'timeKeeper' in self.__dict and self.timeKeeper != None:

						# Check wall times
						canRunNextTask = self.checkTime()

					# Break loop if not last task and cannot run next task
					if len(self.todoDict['Items']) != 0 and canRunNestTask == 0:
						print('Breaking Loop due to elapsing wall time')
						break

					# Handle last task
					elif len(taskScriptKeys) == 0:
						canRunNextTask = 1

			# Handle unavailable items
			else:

				# Increment lockStreak
				print('\nConflict raised on item, proceeding to the next item')
				self.lockStreak += 1

				# Update todo list at 3 consecutive conflicts
				if self.lockStreak == 3:
					print('\nUpdating the todo items list after 3 consecutive conflicts')
					self.todoDict = self.getToDoItems('todo', pyanamo_fields = 'itemID, taskID, lockID, instanceID, ItemState, Log, Log_Length, TaskScript')
					self.lockStreak = 0

				# Proceed to next iteration
				time.sleep(random.randint(1, 4))
				continue


			# Update counter
			self.doneTasks["N"] += 1
			self.doneTasks["Items"].append(itemID)
			time.sleep(random.randint(1, 4))

		# Print completion summary
		print("\nProcessing complete, processed N items = " + str(self.doneTasks["N"]))


	# Update and consult the PyAnamo timeKeeper
	def checkTime(self):

		# Check if object
		if self.timeKeeper == None or 'timeKeeper' not in self.__dict__:
			print('Time Keeper not set, skipping wall time check on active task')
			out = int(1)

		# Otherwise update and check wall time
		else:
			print('Consulting PyAnamo Time Keeper for next iteration')
			self.timeKeeper.updateCurrentTime()
			try:
				print('Can sh-queeze in another der luv')
				self.timeKeeper.check_ElapsedTime()
				out = int(1)

			except pyanamo_errors.TimeKeeperError:
				print('No time left')
				out = int(0)

		# Return check status
		return(out)
