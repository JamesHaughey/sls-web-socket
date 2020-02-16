import json
import logging

logger = logging.getLogger("handler_logger")
logger.setLevel(logging.DEBUG)

def ping(event, context):
    logger.info("Ping requested.")
    body = {
        "message": "Pong!",
        "input": event
    }

    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    return response
