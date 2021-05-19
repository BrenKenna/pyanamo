#!/usr/bin/python


# Import modules
import boto3, time, string, random, re, os, time, sys, json, gzip
from datetime import datetime
import client as pc
import modifier as pm
import executor
import runner
import multiprocessing as mp


# Sub-class to allow single item pool to spawn a nested item pool
class NoDaemonProcess(mp.Process):
	def _get_daemon(self):
		return False
	def _set_daemon(self, value):
		pass
	daemon = property(_get_daemon, _set_daemon)

class NoDaemonContext(type(mp.get_context())):
    Process = NoDaemonProcess

class PyAnamo_ProcessPool(mp.pool.Pool):
	def __init__(self, *args, **kwargs):
		kwargs['context'] = NoDaemonContext()
		super(PyAnamo_ProcessPool, self).__init__(*args, **kwargs)


# Parallelize item processing
def parallel_items(aws_kwargs):

	# Stagger start times of current process
	N = float(random.randint(10, 40) / 100)
	N_2 = float(random.randint(10, 30) / 100)
	N_3 = float(random.randint(1, 15) / 100)
	time.sleep(N + N_2 + N_3)

	# Setup
	dynamodb = boto3.resource('dynamodb', region_name = aws_kwargs['region'])
	table = dynamodb.Table(aws_kwargs['dynamo_table'])

	# Instatiate PyAnamo runner
	pyanamoRunner = runner.PyAnamo_Runner(table, aws_kwargs['s3_key'], Parallel_Nests = aws_kwargs['nests'], aws_region = aws_kwargs['region'], todoDict = 'get', timeLimit = aws_kwargs['timeLimit'])
	logging = pyanamoRunner.processItems()
	return(logging)


# Parallelize nested item processing
def parallel_nested(todo_item):

	# Stagger start times of current process
	N = float(random.randint(10, 40) / 100)
	N_2 = float(random.randint(10, 30) / 100)
	N_3 = float(random.randint(1, 15) / 100)
	time.sleep(N + N_2 + N_3)


	# Setup dynamo session for table
	aws_kwargs = todo_item['aws_kwargs']
	dynamodb = boto3.resource('dynamodb', region_name = aws_kwargs['region'])
	table = dynamodb.Table(aws_kwargs['dynamo_table'])


	# Instantiate PyAnamo Runner without getting new todoDict: (self, dynamo_table, s3Bucket = None, Parallel_Nests = 0, aws_region = None, todoDict = None, timeLimit = None)
	pyanamoRunner = runner.PyAnamo_Runner(table, s3Bucket = aws_kwargs['s3_key'], timeLimit = aws_kwargs['timeLimit'])
	pyanamoRunner.handleNestedItem(todo_item)


# Single items
def single_items(aws_kwargs, Nprocesses, Nested_Processes = 0):

	# Initialize multiprocessing pools: N or mp.cpu_count()
	availableThreads = mp.cpu_count()
	if Nprocesses > availableThreads:
		Nprocesses = availableThreads
	pool = PyAnamo_ProcessPool(Nprocesses)
	aws_kwargs.update( {'nests': Nested_Processes} )

	# Set vars for function
	if 'region' in list(aws_kwargs.keys()) and 'dynamo_table' in list(aws_kwargs.keys()) and 's3_key' in list(aws_kwargs.keys()):

		# Setup work
		work = []
		for i in range(0, Nprocesses):
			work.append(aws_kwargs)

		# Run
		pool.map(parallel_items, work)
		pool.close()
		pool.join()

	# Otherwise pass
	else:
		print('\nError malformed input kwargs dict for parallel processing\n')


# Nested items
def nested_items(nested_item, Nprocesses, aws_kwargs):

	# Initialize multiprocessing pools: N or mp.cpu_count()
	availableThreads = mp.cpu_count()
	if Nprocesses > availableThreads:
		Nprocesses = availableThreads

	pool = PyAnamo_ProcessPool(Nprocesses)

	# Handle tasks per process
	taskPerProcess = int(len(nested_item['TaskScript'].keys()) / Nprocesses)
	if taskPerProcess == 0:
		Nprocesses = len(nested_item['TaskScript'].keys())
		taskPerProcess = int(len(nested_item['TaskScript'].keys()) / Nprocesses)
		print('\nUpdated parallel process pool N = ' + str(taskPerProcess) + ' tasks per N = ' + str(Nprocesses) + ' processes\n')


	# Distribute work todo per process
	chunks = [ list(nested_item['TaskScript'].keys())[i:i + taskPerProcess] for i in range(0, len(nested_item['TaskScript'].keys()), taskPerProcess) ]


	# Compose todo_item dicts for each parallel pool
	para_list = [ ]
	for chunk in chunks:

		# Re-create todo_item dict for each required process
		data = {}
		for todoKey in nested_item.keys():
			data.update( {todoKey: nested_item[todoKey]} )
			data['TaskScript'] = {}
			data.update( {'aws_kwargs': aws_kwargs} )

			# Add the nested task data to the appropriate task script
			for task in chunk:
				data['TaskScript'].update( { task: nested_item['TaskScript'][task] } )

		# Add dict to the process list
		para_list.append(data)


	# Run processes
	pool.map(parallel_nested, para_list)
	pool.close()
	pool.join()


##########################################
##########################################
# 
# Parallelize Runner or Executor
# 
##########################################
##########################################


# Run single item parallelization
def singleItem_main(Nprocesses, Nested_Processes = None, aws_kwargs = None):

	# Run parallel_items
	if aws_kwargs != None:

		# Handle nested parallization
		if Nested_Processes != None and Nested_Processes > 1:

			# Call single item function
			single_items(aws_kwargs, Nprocesses, Nested_Processes)

		else:

			# Call single item function
			single_items(aws_kwargs, Nprocesses)

	# Otherwise exit
	else:
		print('\nError, no dict provided for single or nested item processing\n')



# Run nested item parallelization
def nestedItem_main(Nprocesses, aws_kwargs = None, nested_item = None):

	# Run parallel_items
	if nested_item != None and Nprocesses > 1:

		# Call nested item function
		nested_items(nested_item, Nprocesses, aws_kwargs)

	# Otherwise exit
	else:
		print('\nError, no dict or process count > 1 provided for nested item processing\n')
