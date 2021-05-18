#!/usr/bin/python3


class TimeKeeperError(Exception):

		# Initialize class
		def __init__(self, *args):
			if args:
				print(args)
				self.message = args[0]
			else:
				self.message = None

		# Different error formats
		def __str__(self):

			if self.message:
				return 'Error processing nested tasks. Not enough time left to process the next nested task {0}'.format(self.message)

			else:
				return 'Error processing nested tasks. Not enough time left to process the next nested task'


# raise TimeKeeperError
# raise TimeKeeperError('')
