# **PyAnamo Schema**

List of key-value pairs: [ { ***item1*** }, { ***item2*** }, { ***item3*** }, { ***itemYYZ*** } ]

Automatically generated fields = ***Nested Tasks, Log, Lock Date, Done Date, lockID***

A nested item holds a collection of tasks to do within its ***TaskScript*** key.

Schema + Definition is below: 
[

​	{

​		**itemID:** User-defined unique identifier for items in a DynamoDB Table (***String***),

​		**taskID:** User-defined non-unique identifier for an item, can equal itemID if non-nested (***String***),

​		**TaskScript:** What gets executed when PyAnamo verifies the item is still available (***Map / Dictionary***),

​		**Log:** Output of executing the task script (***Map / Dictionary***), 

​		**ItemState:** todo, locked or done (***String***),

​		**InstanceID:** AWS-Batch JobID, EC2 instance ID or Public IP of computer that locked the item (***String***),

​		**Log_Length:** New line character count of stdout + stderr if single item, or count of how many nested tasks are “done” (***Number***),

​		**Lock_Date:** Date at which the item was locked (***String***),

​		**Done_Date:** Date at which the was marked done (***String***),

​		**Nested_Tasks:** Count of the total nested tasks for the item (***Number***),

​		**lockID:** Randomly generated string to prevent multiple instance pyanamo fetching + processing the same item (***String***)

}

]

# Global Secondary Indexes

[

​	{

​		"IndexName": "**ItemStateIndex**",

​		"KeySchema": [ { "AttributeName": "***ItemState***", "KeyType": "HASH" }, { "AttributeName": "***itemID***", "KeyType": "RANGE" } ],

​		"Projection": { "ProjectionType": "ALL" }, "ProvisionedThroughput": { "ReadCapacityUnits": 10, "WriteCapacityUnits": 5 }

​	},

​	{

​		"IndexName": "**TaskStateIndex**",

​		 "KeySchema": [ { "AttributeName": "***ItemState***", "KeyType": "HASH" }, { "AttributeName": "***taskID***", "KeyType": "RANGE" }],

​		"Projection": { "ProjectionType": "ALL" }, "ProvisionedThroughput": { "ReadCapacityUnits": 10, "WriteCapacityUnits": 5 }

​	},

​	{

​		"IndexName": "**InstanceStateIndex**",

​		"KeySchema": [ { "AttributeName": "***ItemState***", "KeyType": "HASH" }, { "AttributeName": "***InstanceID***", "KeyType": "RANGE" } ],

​		"Projection": { "ProjectionType": "ALL" }, "ProvisionedThroughput": { "ReadCapacityUnits": 10, "WriteCapacityUnits": 5 }

​	},

​	{

​		"IndexName": "**LoggingIndex**",

​		"KeySchema": [ { "AttributeName": "***ItemState***", "KeyType": "HASH" }, { "AttributeName": "***Log_Length***", "KeyType": "RANGE" } ],

​		"Projection": { "ProjectionType": "ALL" }, "ProvisionedThroughput": { "ReadCapacityUnits": 10, "WriteCapacityUnits": 5 }

​	}

]