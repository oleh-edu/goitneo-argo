import json
def handler(event, context):
    print("Logging metrics...")
    metrics = {"accuracy": 0.93, "loss": 0.21}
    return {"statusCode": 200, "body": json.dumps({"logged": True, "metrics": metrics, "input": event})}
