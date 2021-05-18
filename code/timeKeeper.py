#!/usr/bin/python3


# Import modules
from datetime import datetime
import timeKeeperError

# Class to monitor wall time through function class
class PyAnamo_TimeKeeper():

	# Initialize self as a dataset
	def __init__(self, timeLimit):

		# Template timing dataset
		creationTime = datetime.now()
		dummyCurrentTime = datetime.now()
		dummyElapsedTime = float( (dummyCurrentTime - creationTime).total_seconds() )
		dummyWallTime = float( (dummyCurrentTime - creationTime).total_seconds() )
		self.timeKeeping = {
			'Time_Limit': timeLimit,
			'Creation_Time': creationTime,
			'Previous_Time': creationTime,
			'Current_Time': dummyCurrentTime,
			'Wall_Time': dummyWallTime,
			'Elapsed_Time': dummyElapsedTime,
			'Elapsed_Time_Data': {'Updates': 0, 'Times': []},
			'Average_Elapsed_Time': dummyElapsedTime,
			'Next_Elapse': dummyElapsedTime + dummyElapsedTime
		}

	# Update current time
	def updateCurrentTime(self):

		# Move last time to previous
		previousTime = self.timeKeeping['Current_Time']
		del self.timeKeeping['Previous_Time']
		self.timeKeeping.update( { 'Previous_Time': previousTime} )

		# Check current, elapsed and wall times
		currentTime = datetime.now()
		elapsedTime = float( (currentTime - self.timeKeeping['Previous_Time']).total_seconds() )
		wallTime = float( (currentTime - self.timeKeeping['Creation_Time']).total_seconds() )

		# Update data
		self.timeKeeping['Wall_Time'] = wallTime
		self.timeKeeping['Current_Time'] = currentTime
		self.timeKeeping['Elapsed_Time'] = elapsedTime
		self.timeKeeping['Elapsed_Time_Data']['Updates'] += 1
		self.timeKeeping['Elapsed_Time_Data']['Times'].append(elapsedTime)
		self.timeKeeping['Average_Elapsed_Time'] = float(sum(self.timeKeeping['Elapsed_Time_Data']['Times']) / len(self.timeKeeping['Elapsed_Time_Data']['Times']))
		self.timeKeeping['Next_Elapse'] = self.timeKeeping['Wall_Time'] + self.timeKeeping['Average_Elapsed_Time']

	# Check data
	def check_ElapsedTime(self):

		# Check if elapsed time is above time limit
		if self.timeKeeping['Wall_Time'] > self.timeKeeping['Time_Limit']:
			print(self.timeKeeping)
			raise timeKeeperError.TimeKeeperError()

		# Otherwise check if safe to elapse another average time
		elif self.timeKeeping['Next_Elapse'] > self.timeKeeping['Time_Limit']:
			print(self.timeKeeping)
			raise timeKeeperError.TimeKeeperError('Not enough time left for the next elapse to occur')

		# Otherwise proceed
		else:
			print('All is well')
