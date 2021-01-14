# Lex-Controller-Lambda 
# Authored by Nykolas Farhangi
# Purpose: Controls Lex Bots generated by DevSecOps-Lex-Builder. Receives current state of Lex bot and returns next state.

# Python Standard Library
import json
import copy

# 3rd Party Libraries
import boto3

def getAction( action ):
    print( action )
    
    if action['name'] == 'query-dynamo':
        dyno_client = boto3.client('dynamodb')
        response = dyno_client.get_item(
            TableName=action['table'],
            Key={ action['key']: { 'S': action['value'] } }, ConsistentRead=True )
        return response['Item'][ action['return_key'] ]['S']
    
    # if action[0] == 'query-dynamo':
    #     table = action[1]
    #     table = table[ table.index('=') + 1: ]
        
    #     key = action[2]
    #     key = key[ key.index('=') + 1: ]
        
    #     value = action[3]
    #     value = value[ value.index('=') + 1: ]
        
    #     response_key = action[4]
    #     response_key = response_key[ response_key.index('=') + 1: ]
        
    #     dyno_client = boto3.client('dynamodb')
    #     response = dyno_client.get_item(
    #         TableName=table,
    #         Key={ key: { 'S': value } }, ConsistentRead=True )

    #     return response['Item'][response_key]['S']
    
# slots = dict of slots
# current = key of dict slots currently pointed at
# recursively scans knowledge base to determine focus
def determineFocus( KNOWLEDGE_BASE, slots, current ):
    print( "=== determineFocus :: Current = " + current + " ===" )

    if slots[ current ] is None: return current
    nextElement = KNOWLEDGE_BASE[ current ][ slots[ current ] ][ "next" ]
    if nextElement is None: return current
    if slots[ nextElement ] is None: return current 

    return determineFocus( KNOWLEDGE_BASE, slots, nextElement )

def getOutput( KNOWLEDGE_BASE, slots, intent, entrySlot ):
    focus = determineFocus( KNOWLEDGE_BASE, slots, entrySlot )
    if focus is None: return None

    print( "Focus :: " + focus )
    output = copy.deepcopy( KNOWLEDGE_BASE[ focus ][ slots[ focus ] ] )
    
    print( "Output = ", output )
    
    # action in fulfillment
    if 'action' in output:
        output['return']['dialogAction']['message'].update({
            "contentType": "PlainText",
            "content": getAction( output['action'] )
        })
        
    if "slotToElicit" in output["return"][ "dialogAction" ]:
        output["return"]["dialogAction"].update({
            "intentName": intent,
            "slots": slots
        })
    
    return output["return"]

def lambda_handler( event, context ):
    print( '\nEvent ===> ', event )
    
    bot = event['bot']['name']
    slots = event['currentIntent']['slots']
    intent = event['currentIntent']['name']

    print( '\nBot Name: ', bot )
    print( '\nRetrieving knowledge base...')
    
    print( 'Knowledge Base Filename: ', 'resources/knowledge base/' + bot + '_knowledge_base.json' )

    s3 = boto3.resource('s3')
    obj = s3.Object( 'stealth-startup-lex', 'resources/knowledge base/' + bot + '_knowledge_base.json' )
    KNOWLEDGE_BASE = json.loads( obj.get()['Body'].read().decode( 'utf8' ) )
    
    print( 'Knowledge Base ===> ', KNOWLEDGE_BASE )

    entrySlot = KNOWLEDGE_BASE['meta'][ intent ]['entrySlot']
    
    print( "\n\nSlots:" )
    print( slots )
    print( "\nCurrent Intent Name: " + intent )
    
    if slots[ entrySlot ] is not None: return getOutput( KNOWLEDGE_BASE, slots, intent, entrySlot )
    
    return {
        "dialogAction": {
            "type": "Delegate",
            "slots": slots
        }
    }