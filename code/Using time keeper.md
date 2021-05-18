## Using time keeper

```python
import timeKeeper
import time

# Test with seconds
timeLimit = float(120)
singleItem_timeKeeper = timeKeeper.PyAnamo_TimeKeeper(timeLimit)
for i in range(0, 10):
	print('\n\n\n')
	print(singleItem_timeKeeper.timeKeeping)
	time.sleep(15)
	singleItem_timeKeeper.updateCurrentTime()
	singleItem_timeKeeper.check_ElapsedTime()

```

