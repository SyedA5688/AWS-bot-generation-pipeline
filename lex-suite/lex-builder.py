# Lex-Builder-Lambda AWS Lambda
# Authored by Nykolas Farhangi
# Purpose: Generates Lex Bot JSON and associated files from a configuration YAML, stores in S3 bucket

# Python Standard Library
import json
import copy
import uuid
import os
import re
from zipfile import ZipFile
import time

# 3rd Party Libraries
# pip install python-dotenv pyyaml
from dotenv import load_dotenv # pip install python-dotenv
import yaml # pip install pyyaml
import boto3
import botocore

load_dotenv()

# Global Variables
memory = { 'verbose': os.getenv( 'verbose' ) == "True", 'priorityCount': 1 }
templates = {}
config = {}

# Script Functions

# Generates a unique name for Slot Type name and Slot name
def generateUniqueName(): return re.sub( '[^a-zA-Z]', '', str( uuid.uuid4() ) )

# Generates response card for a slot
def generateResponseCard( values, title=None ):
    if title is None: title = 'Options'
    output = '{\"version\":1,\"contentType\":\"application/vnd.amazonaws.card.generic\",\"genericAttachments\":[{\"title\":\"' + title + '\",\"buttons\":['
    for value in values: output += '{\"text\":\"' + value[ 'value' ].title() + '\",\"value\":\"' + value[ 'value' ] + '\"}' + ( ',' if value != values[ -1 ] else '' )
    output += "]}]}"
    return output

# parseIntent( entry, digested )
# entry :: dict, list element of tree or branch. represents AWS Lex slot
# digested :: dict, has keys: slots, slot_types, knowledge_base

def parseIntent( entry, digested={ 'slots': [], 'slot_types': [], 'knowledge_base': {}, 'slot_type_values': [], 'knowledge_base_child': {} } ):
    # For Parent Recursion Variables
    slot_type_values = []
    knowledge_base_child = {}

    for element in entry:
        if 'branch' in element.keys():
            if 'prompt' not in element.keys():
                print( '\n\n !! ERROR !! Element should have "prompt" key. \nElement: ' )
                print( element )
                continue

            # create and populate slot type
            slot_type = copy.deepcopy( templates[ 'slot_type_outline' ] )
            slot_type[ 'name' ] = generateUniqueName()

            # create and populate new slot
            # populate values: slotType, valueElicitationPrompt, name
            slot = copy.deepcopy( templates[ 'slot_outline' ] )
            slot[ 'slotType' ] = slot_type[ 'name' ]
            slot[ 'name' ] = element[ 'name' ] if 'name' in element.keys() else generateUniqueName()

            # slot prompts
            prompts = []
            if isinstance( element[ 'prompt' ], list ):
                for prompt in element[ 'prompt' ]: prompts.append( { 'contentType': 'PlainText', 'content': prompt } )
            else: prompts.append( { 'contentType': 'PlainText', 'content': element[ 'prompt' ] } )
            slot[ 'valueElicitationPrompt' ][ 'messages' ] = prompts

            # slot priority
            slot[ 'priority' ] = memory[ 'priorityCount' ]
            if slot[ 'priority' ] == 1:
                slot[ 'slotConstraint' ] = 'Required'
                digested[ 'knowledge_base' ].update( { 'meta': { memory[ 'currentIntent' ]: { 'entrySlot': slot[ 'name' ] } } } )
            memory.update( { 'priorityCount': memory[ 'priorityCount' ] + 1 } )

            nextDigested = parseIntent( element[ 'branch' ] )

            slot_type[ 'enumerationValues' ] = nextDigested[ 'slot_type_values' ]

            slot[ 'valueElicitationPrompt' ].update( { 'responseCard': generateResponseCard( nextDigested[ 'slot_type_values' ] ) } )

            if 'option' in element.keys():
                slot_type_values.append( { 'value': element[ 'option' ] } )

                knowledge_base_child.update( {
                    element[ 'option' ]: {
                        'next': slot[ 'name' ],
                        'return': {
                            'dialogAction': {
                                'type': 'ElicitSlot',
                                'slotToElicit': slot[ 'name' ]
                            }
                        }
                    }
                } )

            digested[ 'slots' ].append( slot )
            digested[ 'slot_types' ].append( slot_type )
            digested[ 'knowledge_base' ].update( { slot[ 'name' ]: nextDigested[ 'knowledge_base_child' ] } )

        elif 'fulfillment' in element.keys():
            if 'option' not in element.keys():
                print( '\n\n!! ERROR !! Element should have "value" key. \nElement: ' )
                print( element )
                continue
            
            slot_type_values.append( { 'value': element[ 'option' ] } )
            
            if isinstance( element['fulfillment'], str ):
                knowledge_base_child.update( {
                    element[ 'option' ]: {
                        'next': None,
                        'return': {
                            "dialogAction": {
                                "type": "Close",
                                "fulfillmentState": "Fulfilled",
                                "message": {
                                    "contentType": "PlainText",
                                    "content": element[ 'fulfillment' ]
                                }   
                            }
                        }
                    }
                } )
            
            elif isinstance( element['fulfillment'], dict ) and 'action' in element['fulfillment'].keys():
                knowledge_base_child.update( {
                    element[ 'option' ]: {
                        'next': None,
                        'action': element['fulfillment']['action'],
                        'return': {
                            "dialogAction": {
                                "type": "Close",
                                "fulfillmentState": "Fulfilled",
                                "message": {
                                    "contentType": "PlainText",
                                    "content": '<REPLACE>'
                                }   
                            }
                        }
                    }
                } )
            

    digested[ 'knowledge_base_child' ] = knowledge_base_child
    digested[ 'slot_type_values' ] = slot_type_values
    return digested

def generateLex( config ):
    s3 = boto3.resource( 's3' )

    # Gets Lex Template
    obj = s3.Object( 'stealth-startup-lex', 'resources/lex_outline.json' )
    templates.update( json.loads( obj.get()['Body'].read().decode( 'utf8' ) ) )
    
    if memory['verbose']:
        print( '\nConfig ===> ', config )
        print( '\nTemplates ===> ', templates )

    # Begin Lex Generation from Config

    lex = {} # Lex Bot json
    knowledge_base = {} # Knowledge Base json
    delete_instructions = [] # Delete Me json

    lex = copy.deepcopy( templates[ 'lex_outline' ] )

    lex[ 'resource' ][ 'name' ] = config[ 'bot_name' ]

    delete_instructions.append( { 'type': 'bot', 'name': lex[ 'resource' ][ 'name' ] } )

    intents = []
    slot_types = []

    for entry in config[ 'intents' ]:
        intent = copy.deepcopy( templates[ 'intent_outline' ] )
        intent[ 'name' ] = entry[ 'name' ]
        intent[ 'sampleUtterances' ] = entry[ 'sample_utterances' ]
        if 'lambda_init' in entry.keys(): intent[ 'dialogCodeHook' ][ 'uri' ] = entry[ 'lambda_init' ]
        memory.update( { 'currentIntent': intent[ 'name' ] } )

        digested = parseIntent( entry[ 'tree' ] )
        intent[ 'slots' ] = digested[ 'slots' ]
        knowledge_base.update( digested[ 'knowledge_base' ] )

        intents.append( intent )
        slot_types += digested[ 'slot_types' ]

        delete_instructions.append( { 'type': 'intent', 'name': intent[ 'name' ] } )
        for slot_type in slot_types: delete_instructions.append( { 'type': 'slot_type', 'name': slot_type[ 'name' ] } )

    lex[ 'resource' ][ 'intents' ] = intents
    lex[ 'resource' ][ 'slotTypes' ] = slot_types

    return { 'lex': lex, 'knowledge_base': knowledge_base, 'delete_instructions': delete_instructions }
    
# AWS Functions

def uploadLexFiles( origin, lex, knowledge_base, delete_instructions ):
    # Creates files in 'tmp' directory in Lambda FS

    lex_filename = lex[ 'resource' ][ 'name' ] + '_lex'
    kb_filename = lex[ 'resource' ][ 'name' ] + '_knowledge_base.json'
    di_filename = lex[ 'resource' ][ 'name' ] + '_delete_me.json'

    #if not os.path.exists('tmp'): os.mkdir('/tmp/')

    with open( '/tmp/' + lex_filename + '.json', 'w+' ) as file: json.dump( lex, file, indent=2 )
    with open( '/tmp/' + kb_filename, 'w+' ) as file: json.dump( knowledge_base, file, indent=2 )
    with open( '/tmp/' + di_filename, 'w+' ) as file: json.dump( delete_instructions, file, indent=2 )

    zipObj = ZipFile( '/tmp/' + lex_filename + '.zip', 'w' )
    zipObj.write( '/tmp/' + lex_filename + '.json', lex_filename + '.json' )
    zipObj.close()

    if memory['verbose']: print( '\nWriting files to "/tmp" folder' )

    # Checks if Lex Bot already exists

    s3 = boto3.resource( 's3' )
    lex_client = boto3.client( 'lex-models' )

    try: s3.Object( 'stealth-startup-lex', 'resources/delete instructions/' + di_filename ).load()
    except botocore.exceptions.ClientError as err:
        if err.response['Error']['Code'] == '404' or err.response['Error']['Code'] == '403':
            # File does not exist! Skip!
            if memory['verbose']: print( '\n"%s" does not exist!'%di_filename )
            pass
        else:
            print( '!! ERROR !! in uploadLexFiles( origin, lex, knowledge_base, delete_instructions )' )
            print( '\tSomething has gone wrong. Error = ', err )
            raise err
    else:
        # File does exist! Delete old Lex resources from AWS Lex!
        print( '\n"%s" exists! Purging old bot...'%di_filename )
        obj = s3.Object( 'stealth-startup-lex', 'resources/delete instructions/' + di_filename )
        old_delete_instructions = json.loads( obj.get()['Body'].read().decode( 'utf8' ) )
        
        # Make 3 attempts
        for i in range(0,3):
            for instruction in old_delete_instructions:
                try:
                    if instruction[ 'type' ] == 'bot': lex_client.delete_bot( name=instruction[ 'name' ] )
                    elif instruction[ 'type' ] == 'intent': lex_client.delete_intent( name=instruction[ 'name' ] )
                    elif instruction[ 'type' ] == 'slot_type': lex_client.delete_slot_type( name=instruction[ 'name' ] )
                    time.sleep( 5 )
                except: pass
        
        print( '\nPurge Complete!' )
        
    #return
        
    # Upload Files to S3
    # If files already exist, will be overwritten

    if memory['verbose']: print( '\nUploading new files to S3...' )

    s3 = boto3.client( 's3' )

    with open( '/tmp/' + lex_filename + '.zip', 'rb' ) as file: s3.upload_fileobj( file, origin['name'], 'output/' + lex_filename + '.zip' )
    with open( '/tmp/' + kb_filename, 'rb' ) as file: s3.upload_fileobj( file, origin['name'], 'resources/knowledge base/' + kb_filename )
    with open( '/tmp/' + di_filename, 'rb' ) as file: s3.upload_fileobj( file, origin['name'], 'resources/delete instructions/' + di_filename )

    if memory['verbose']:
        print( '\nUpload Complete!' )
        print( '\nImporting Lex to AWS Lex...' )

    # Import Lex
    with open( '/tmp/' + lex_filename + '.zip', 'rb' ) as file:
        response = lex_client.start_import(
            payload=file.read(),
            resourceType='BOT',
            mergeStrategy='OVERWRITE_LATEST'
        )
        
    print( 'Lex Bots ===> ', lex_client.get_bots() )

    if memory['verbose']: print( '\nImport Complete!' )

    # Delete 'tmp' directory in Lambda FS
    #shutil.rmtree( '/tmp/' )

# Entry Points

def lambda_handler( event, context ):
    # Initialize Global Variables
    memory = { 'verbose': os.getenv( 'verbose' ) == "True", 'priorityCount': 1 }
    templates = {}
    config = {}

    print( '\nGenerate Lex Lambda :: Verbose ' + ('Enabled' if memory['verbose'] else 'Disabled') )

    print( '\nEvent ===> ', event, '\n' )

    origin = event[ 'Records' ][0][ 's3' ][ 'bucket' ]
    if memory['verbose']: print( 'Origin ===> ', origin )

    trigger = event[ 'Records' ][0][ 's3' ][ 'object' ][ 'key' ]
    if memory['verbose']: print( '\nTrigger ===> ', trigger )
    
    s3 = boto3.resource( 's3' )

    # Gets Triggering Configuration File
    obj = s3.Object( origin[ 'name' ], trigger )
    config.update( yaml.full_load( obj.get()['Body'].read() )['config'] )

    generated = generateLex( config )
    
    if memory[ 'verbose' ]:
        print( '\nLex ===> ', generated[ 'lex' ] )
        print( '\nKnowledge Base ===> ', generated[ 'knowledge_base' ] )
        print( '\nDelete Instructions ===> ', generated[ 'delete_instructions' ] )

    uploadLexFiles( origin, generated[ 'lex' ], generated[ 'knowledge_base' ], generated[ 'delete_instructions' ] )

    print( '\nLex bot "%s" has been successfully generated.\n'%generated[ 'lex' ][ 'resource' ][ 'name' ] )
    
def test():
    config = None
    with open('./configs/chatbot_config.yml', 'r') as file: config = yaml.full_load( file )
    output = generateLex(config['config'])
    print( output )
    
test()