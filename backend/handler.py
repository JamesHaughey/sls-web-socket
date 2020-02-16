import json


def ping(event, context):
    body = {
        "message": "Pong!",
        "input": event
    }

    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    return response

    # Use this code if you don't use the http event with the LAMBDA-PROXY
    # integration
    """
    return {
        "message": "Pong!",
        "event": event
    }
    """
