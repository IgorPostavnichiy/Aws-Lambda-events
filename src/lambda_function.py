import boto3
import json

sts = boto3.client('sts')
s3 = boto3.resource('s3')
ec2 = boto3.client('ec2')

def is_self_invocation(detail):
    try:
        identity = sts.get_caller_identity()
        if 'userIdentity' in detail:
            if 'arn' in detail['userIdentity'] and 'Arn' in identity:
                if identity['Arn'] == detail['userIdentity']['arn']:
                    return True
    except ClientError as e:
        print('STS Error: {0}'.format(e))

    return False

def get_bucket_name(instance_id):
    response = ec2.describe_instances(InstanceIds=[instance_id])
    instances = response['Reservations'][0]['Instances']
    for instance in instances:
        for tag in instance['Tags']:
            if tag['Key'] == 'Bucket':
                return tag['Value']
    return None

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
                            objects = list(bucket.objects.all())
                            if objects:
                                # Clearing the S3 bucket if it contains objects
                                bucket.delete_objects(
                                    Delete={
                                        'Objects': [{'Key': obj.key} for obj in objects]
                                    }
                                )
                                print(f"Removed objects from the S3 bucket {bucket_name}")
                            # Deleting the S3 bucket if it is empty
                            if len(list(bucket.objects.all())) == 0:
                                bucket.delete()
                                print(f"S3 bucket {bucket_name} deleted")

    return json.dumps({
        'result': 'SUCCESS',
        'data': 'It worked!'
    })
