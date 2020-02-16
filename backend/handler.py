import boto3
import json
import logging
import time

logger = logging.getLogger("handler_logger")
logger.setLevel(logging.DEBUG)

dynamodb = boto3.resource("dynamodb")

def ping(event, context):
    logger.info("Ping requested.")
    
    # TESTING: Making sure the database works
    table = dynamodb.Table("serverless-chat_Messages")
    timestamp = int(time.time())
    table.put_item(
        Item={
            "Room"      : "general",
            "Index"     : 0,
            "Timestamp" : timestamp,
            "Username"  : "ping-user",
            "Content"   : "PING!"
        }
    )
    logger.debug("Item added to the database.")
    
    body = {
        "message": "Pong!",
        "input": event
    }

    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    return response
