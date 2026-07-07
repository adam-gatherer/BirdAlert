import json

# placeholder
def lambda_handler(event, context):
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "BirdAlert poller is running."
        })
    }