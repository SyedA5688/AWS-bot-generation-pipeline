import pandas as pd

import boto3

dynamodb = boto3.client('dynamodb')
response = dynamodb.get_item(
            TableName='chatbot-texts',
            Key={ 'title': { 'S': 'Customer Premises Personnel'} }, ConsistentRead=True )

print( response )