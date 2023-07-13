import boto3
import json
import logging

sts = boto3.client('sts')
s3 = boto3.resource('s3')
ec2 = boto3.client('ec2')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def is_self_invocation(detail):
    try:
        identity = sts.get_caller_identity()
        if 'userIdentity' in detail:
            if 'arn' in detail['userIdentity'] and 'Arn' in identity:
                if identity['Arn'] == detail['userIdentity']['arn']:
                    return True
    except ClientError as e:
        logger.error('STS Error: {0}'.format(e))

    return False

def get_bucket_name(instance_id):
    response = ec2.describe_instances(InstanceIds=[instance_id])
    instances = response['Reservations'][0]['Instances']
    for instance in instances:
        for tag in instance['Tags']:
            if tag['Key'] == 'S3-Owner':
                return tag['Value']
    return None

def should_wipe_bucket(instance_id):
    response = ec2.describe_instances(InstanceIds=[instance_id])
    instances = response['Reservations'][0]['Instances']
    for instance in instances:
        for tag in instance['Tags']:
            if tag['Key'] == 'S3-Wipe':
                return tag['Value'] == 'true'
    return False

def wipe_bucket(bucket):
    try:
        bucket.objects.all().delete()
        logger.info(f"Wiped S3 bucket {bucket.name} recursively")
    except Exception as e:
        logger.error(f"Error wiping S3 bucket {bucket.name}: {str(e)}")

def lambda_handler(event, context):
    if 'detail' in event:
        detail = event['detail']
        if is_self_invocation(detail):
            return json.dumps({
                'result': 'FAILURE',
                'data': 'Self invocation via CloudWatch Event'
            })
        if 'requestParameters' in detail:
            if detail['requestParameters']['eventType'] == 'AwsApiCall':
                if detail['requestParameters']['eventName'] == 'TerminateInstances':
                    instance_ids = [i['instanceId'] for i in detail['resources']]
                    for instance_id in instance_ids:
                        bucket_name = get_bucket_name(instance_id)
                        if bucket_name:
                            bucket = s3.Bucket(bucket_name)
                            if should_wipe_bucket(instance_id):
                                wipe_bucket(bucket)
                            else:
                                objects = list(bucket.objects.all())
                                if objects:
                                    try:
                                        # Clearing the S3 bucket if it contains objects
                                        bucket.delete_objects(
                                            Delete={
                                                'Objects': [{'Key': obj.key} for obj in objects]
                                            }
                                        )
                                        logger.info(f"Removed objects from the S3 bucket {bucket.name}")
                                    except Exception as e:
                                        logger.error(f"Error removing objects from S3 bucket {bucket.name}: {str(e)}")

                                # Deleting the S3 bucket if it is empty
                                if len(list(bucket.objects.all())) == 0:
                                    try:
                                        bucket.delete()
                                        logger.info(f"S3 bucket {bucket.name} deleted")
                                    except Exception as e:
                                        logger.error(f"Error deleting S3 bucket {bucket.name}: {str(e)}")

    return json.dumps({
        'result': 'SUCCESS',
        'data': 'It worked!'
    })
