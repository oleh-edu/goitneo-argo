import json
def handler(event, context):
    print("Validating data...")
    # conditional validation logic can be added here
    result = {"validated": True, "details": "basic checks passed"}
    return {"statusCode": 200, "body": json.dumps(result), "input": event}
