import json
import boto3
import os

def lambda_handler(event, context):
    pipeline_name = os.environ['PIPELINE_NAME']
    client = boto3.client('codepipeline')
    
    response = client.start_pipeline_execution(name=pipeline_name)

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f'Successfully triggered {pipeline_name}',
            'pipeline_execution_id': response['pipelineExecutionId']
        })
    }