#!/usr/bin/python


# Import modules
import boto3, time, string, random, re, os, time, sys, json, gzip
from datetime import datetime
import client as pc
import modifier as pm
import executor
import runner
import multiprocessing as mp


# Parallelize item processing
def parallel_items(aws_kwargs):

	# Stagger start times of current process
	N = float(random.randint(1, 30) / 100)
	N_2 = float(random.randint(1, 20) / 100)
	N_3 = float(random.randint(1, 10) / 100)
	time.sleep(N + N_2 + N_3)

	# Setup
	dynamodb = boto3.resource('dynamodb', region_name = aws_kwargs['region'])
	table = dynamodb.Table(aws_kwargs['dynamo_table'])

	# Instatiate PyAnamo runner
	pyanamoRunner = runner.PyAnamo_Runner(table, aws_kwargs['s3_key'], Parallel_Nests = aws_kwargs['nests'], todoDict = 'get')
	logging = pyanamoRunner.processItems()
	return(logging)


# Sub-classes to allow single item pool to spawn a pool for nested items
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


# Single items
def single_items(aws_kwargs, Nprocesses, Nested_Processes = 0):

	# Initialize multiprocessing pools: N or mp.cpu_count()
	availableThreads = mp.cpu_count()
	pool = PyAnamo_ProcessPool(Nprocesses)
	aws_kwargs.update( {'nests': Nested_Processes} )

	# Set vars for function
	if 'region' in list(aws_kwargs.keys()) and 'dynamo_table' in list(aws_kwargs.keys()) and 's3_key' in list(aws_kwargs.keys()):

		# Setup work
		work = []
		for i in range(0, Nprocesses):
			work.append(aws_kwargs)

		# Run
		pool.__dict__
		pool.map(parallel_items, work)
		pool.close()
		pool.join()

	# Otherwise pass
	else:
		print('\nError malformed input kwargs dict for parallel processing\n')


# Run
def main(Nprocesses, Nested_Processes = None, aws_kwargs = None):

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
