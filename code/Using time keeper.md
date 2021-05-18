## Using time keeper

```python
# Import modules
import timeKeeper
import pyanamo_errors
import time, sys

# Test with seconds
timeLimit = float(43)
singleItem_timeKeeper = timeKeeper.PyAnamo_TimeKeeper(timeLimit)
for i in range(0, 20):
	print('\n\n\n')
	print(singleItem_timeKeeper.timeKeeping)
	time.sleep(15)
	try:
		singleItem_timeKeeper.updateCurrentTime()
		singleItem_timeKeeper.check_ElapsedTime()
	except pyanamo_errors.TimeKeeperError:
		print('Done, no time left. Unlocking item')
		sys.exit()
```

