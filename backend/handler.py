import boto3
import json
import logging
import time

logger = logging.getLogger("handler_logger")
logger.setLevel(logging.DEBUG)

dynamodb = boto3.resource("dynamodb")

def _get_response(status_code, body):
    if not isinstance(body, str):
        body = json.dumps(body)
    return {"statusCode": status_code, "body": body}

def _get_body(event):
    try:
        return json.loads(event.get("body", ""))
    except:
        logger.debug("event body count not be JSON decoded.")
        return {}

def _send_to_connection(connection_id, data, event):
    domainName = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]
    gatewayapi = boto3.client(
        "apigatewaymanagementapi",
        endpoint_url = f"https://{domainName}/{stage}"
    )
    return gatewayapi.post_to_connection(
        ConnectionId=connection_id,
        Data=json.dumps(data).encode('utf-8')
    )
    
def _get_next_index(room):
    table = dynamodb.Table("serverless-chat_Messages")
    response = table.query(
        KeyConditionExpression="Room = :room",
        ExpressionAttributeValues={":room": room},
        Limit=1,
        ScanIndexForward=False
    )
    items = response.get("Items", [])
    return items[0]["Index"] +1 if len(items) > 0 else 0

def send_message(event, context):
    """
    When a message is sent of the socket, forward it to all connections.
    """
    logger.info("Message sent on WebSocket.")
    
    # Ensure all required fields were provided
    body = _get_body(event)
    for attribute in ["username", "content"]:
        if attribute not in body:
            logger.debug(f"Failed: '{attribute}' not in message dict.")
            return _get_response(400, f"'{attribute}' not in message dict.")
        
    # Get the next message index
    index = _get_next_index("general")
    
    # Add the new message to the database
    timestamp = int(time.time())
    username = body["username"]
    content = body["content"]
    table = dynamodb.Table("serverless-chat_Messages")
    table.put_item(
        Item={
            "Room": "general",
            "Index": index,
            "Timestamp" : timestamp,
            "Username"  : username,
            "Content"   : content
        }
    )
    
    # Get all current connections
    table = dynamodb.Table("serverless-chat_Connections")
    response = table.scan(ProjectionExpression="ConnectionID")
    items = response.get("Items", [])
    connections = [x["ConnectionID"] for x in items if "ConnectionID" in x]
    
    # Send the message data to all connections
    message = {
        "username" : username,
        "content" : content,
    }
    logger.debug(f"Broadcasting message: {message}")
    data = {"messages": [message]}
    for connectionID in connections:
        _send_to_connection(connectionID, data, event)
        
    return _get_response(200, "Message sent to all connections.")

def get_recent_messages(event, context):
    """
    Return the 10 most recent chat messages.
    """
    logger.info("Retrieving most recent messages.")
    connectionID = event["requestContext"].get("connectionID")
    
    # Get the 10 most recent chat messages
    room = "general"
    
    table = dynamodb.Table("serverless-chat_Messages")
    response = table.query(
        KeyConditionExpression="Room = :room",
        ExpressionAttributeValues={":room": room},
        Limit=10,
        ScanIndexForward=False
    )
    items = response.get("Items", [])
    
    # Extract the relevant data and order chronologically
    messages = [
        {"username": x["username"], "content": x["content"]}
        for x in items
    ]
    messages.reverse()
    
    # Send them to the client who asked for it
    data = {"messages": messages}
    _send_to_connection(connectionID, data, event)
    return _get_response(200, "Send recent messages.")
    
def connection_manager(event, context):
    """
    Handles connecting and disconecting for the Websocket.
    """
    connectionID = event["requestContext"].get("connectionId")
    
    if event["requestContext"]["eventType"] == "CONNECT":
        logger.info(f"Connect requested: {connectionID}")
        
        # Add connectionID to the database
        table = dynamodb.Table("serverless-chat_Connections")
        table.put_item(Item={"ConnectionID": connectionID})
        return _get_response(200, "Connect succesful.")

    elif event["requestContext"]["eventType"] == "DISCONNECT":
        logger.info(f"Disconnect requested : {connectionID}")
        
        # Remove connectionID from the database
        table = dynamodb.Table("serverless-chat_Connections")
        table.delete_item(Key={"ConnectionID": connectionID})
        return _get_response(200, "Disconnect succesful.")
    
    else:
        logger.error("Connection manager eceived unrecognized eventType.")
        return _get_response(500, "Unrecognized eventType.")

def default_message(event, context):
    """
    Send back error when unrecognized WebSocket action is received.
    """
    logger.info("Unrecognized WebSocket action received.")
    return _get_response(400, "Unrecognized WebSocket action.")

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
