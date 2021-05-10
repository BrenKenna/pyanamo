############################
############################
# 
# Modifier Class
# 
############################
############################


# Test out
python
import boto3
import modifier as pm


# Initialize modifier
dynamodb = boto3.resource('dynamodb', region_name = 'us-east-1')
table = dynamodb.Table('Testing')
pyanamoModifier = pm.PyAnamo_Modifier(table)



# Run functions
itemID = int(34)
lockID = pyanamoModifier.generateLockID()
instanceID = pyanamoModifier.getInstanceID()
pyanamoModifier.lockItem(itemID, lockID, instanceID)
lockVerified = pyanamoModifier.verifyItem(itemID)
