#!/usr/bin/python3


# Import modules
from datetime import datetime
import pyanamo_errors


# Class to monitor wall time through function class
class PyAnamo_TimeKeeper():

	# Initialize self as a dataset
	def __init__(self, timeLimit):

		# Template timing dataset
		creationTime = datetime.now()
		dummyCurrentTime = datetime.now()
		dummyElapsedTime = round(float((dummyCurrentTime - creationTime).total_seconds()), 1)
		dummyWallTime = round(float((dummyCurrentTime - creationTime).total_seconds()), 1)
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
		self.timeKeeping['Previous_Time'] = self.timeKeeping['Current_Time']

		# Check current, elapsed and wall times
		currentTime = datetime.now()
		elapsedTime = round(float( (currentTime - self.timeKeeping['Previous_Time']).total_seconds()), 1)
		wallTime = round(float( (currentTime - self.timeKeeping['Creation_Time']).total_seconds()), 1)

		# Update data
		self.timeKeeping['Wall_Time'] = wallTime
		self.timeKeeping['Current_Time'] = currentTime
		self.timeKeeping['Elapsed_Time'] = elapsedTime
		self.timeKeeping['Elapsed_Time_Data']['Updates'] += 1

		# Stop times list from getting too big
		if len(self.timeKeeping['Elapsed_Time_Data']['Times']) == 15:
			self.timeKeeping['Elapsed_Time_Data']['Times'] = [ round(self.timeKeeping['Average_Elapsed_Time'], 1) ]
			self.timeKeeping['Elapsed_Time_Data']['Times'].append(elapsedTime)

		else:
			self.timeKeeping['Elapsed_Time_Data']['Times'].append(elapsedTime)

		self.timeKeeping['Average_Elapsed_Time'] = round(float(sum(self.timeKeeping['Elapsed_Time_Data']['Times']) / len(self.timeKeeping['Elapsed_Time_Data']['Times'])), 1)
		self.timeKeeping['Next_Elapse'] = round(self.timeKeeping['Wall_Time'] + self.timeKeeping['Average_Elapsed_Time'], 1)

	# Check data
	def check_ElapsedTime(self):

		# Check if elapsed time is above the specified time limit
		if self.timeKeeping['Wall_Time'] > self.timeKeeping['Time_Limit']:
			raise pyanamo_errors.TimeKeeperError(str('Wall time limit of ' + str(self.timeKeeping['Time_Limit']) + 's has exceeded with ' + str(self.timeKeeping['Wall_Time']) + 's' ))

		# Otherwise check if it is safe to elapse another average time
		elif self.timeKeeping['Next_Elapse'] > self.timeKeeping['Time_Limit']:
			raise pyanamo_errors.TimeKeeperError(str('Not enough time left for the next elapse to occur. Next elapsed time on average will be ' + str(self.timeKeeping['Next_Elapse']) + 's, wall time limit = ' + str(self.timeKeeping['Time_Limit']) + 's'))

		# Otherwise proceed
		else:
			pass
