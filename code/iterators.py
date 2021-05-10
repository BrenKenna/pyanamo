#!/usr/bin/python


# Import modules
import boto3, string, re, os, time, sys, json, gzip
from subprocess import Popen, PIPE
from datetime import datetime
from client import PyAnamo_Client
from modifier import PyAnamo_Modifier


# Iterate over todo items
class PyAnamo_Runner(PyAnamo_Client, PyAnamo_Modifier, PyAnamo_Executor):

	# Initialize class
	def __init__(self, dynamo_table):
		PyAnamo_Client.__init__(self, dynamo_table)
		self.pyanamoModifier = PyAnamo_Modifier(table)


	# 
