#!/usr/bin/python


table = client.create_table(
    TableName=tbl,
    KeySchema=[{ 'AttributeName': 'itemID', 'KeyType': 'HASH'}],
    AttributeDefinitions=[
            { 'AttributeName': 'itemID', 'AttributeType': 'S' },
            { 'AttributeName': 'taskID', 'AttributeType': 'S' },
            { 'AttributeName': 'ID_Index', 'AttributeType': 'S' },
            { 'AttributeName': 'lockID', 'AttributeType': 'S' },
            { 'AttributeName': 'Log', 'AttributeType': 'S' },
            { 'AttributeName': 'Lock_Date', 'AttributeType': 'S' },
            { 'AttributeName': 'Done_Date', 'AttributeType': 'S' },
            { 'AttributeName': 'Log_Length', 'AttributeType': 'S' },
            { 'AttributeName': 'TaskScript', 'AttributeType': 'S' },
    ],
    GlobalSecondaryIndexes=[
            {
               "IndexName": "TaskIndex",
               "KeySchema": [ { "AttributeName": "taskID", "KeyType": "HASH" }, { "AttributeName": "ID_Index", "KeyType": "RANGE" }],
               "Projection": { "ProjectionType": "ALL" },
               "ProvisionedThroughput": { "ReadCapacityUnits": 10, "WriteCapacityUnits": 5 }
            },
            {
               "IndexName": "LoggingIndex",
               "KeySchema": [ { "AttributeName": "lockID", "KeyType": "HASH" }, { "AttributeName": "Log", "KeyType": "RANGE" } ],
               "Projection": { "ProjectionType": "ALL" }, "ProvisionedThroughput": { "ReadCapacityUnits": 10, "WriteCapacityUnits": 5 }
            },
            {
               "IndexName": "DateIndex",
               "KeySchema": [ { "AttributeName": "Lock_Date", "KeyType": "HASH" }, { "AttributeName": "Done_Date", "KeyType": "RANGE" } ],
               "Projection": { "ProjectionType": "ALL" }, "ProvisionedThroughput": { "ReadCapacityUnits": 10, "WriteCapacityUnits": 5 }
            },
            {
               "IndexName": "ScriptIndex",
               "KeySchema": [ { "AttributeName": "Log_Length", "KeyType": "HASH" }, { "AttributeName": "TaskScript", "KeyType": "RANGE" } ],
               "Projection": { "ProjectionType": "ALL" }, "ProvisionedThroughput": { "ReadCapacityUnits": 10, "WriteCapacityUnits": 5 }
            }
    ],
    ProvisionedThroughput={ 'ReadCapacityUnits': 10, 'WriteCapacityUnits': 10 }
)

