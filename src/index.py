import yaml
import boto3
import json

sts = boto3.client('sts')
s3 = boto3.resource('s3')

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

def handler(event, context):

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
                        bucket_name = 'lambda_bucket_test'  # Замените на имя вашего S3-ведра
                        bucket = s3.Bucket(bucket_name)
                        objects = list(bucket.objects.all())
                        
                        if objects:
                            # Очистка S3-ведра, если в нем есть объекты
                            bucket.delete_objects(
                                Delete={
                                    'Objects': [{'Key': obj.key} for obj in objects]
                                }
                            )
                            print(f"Удалены объекты из S3-ведра {bucket_name}")
                            
                        # Удаление S3-ведра, если он пустой
                        if len(list(bucket.objects.all())) == 0:
                            bucket.delete()
                            print(f"S3-ведро {bucket_name} удалено")

    return json.dumps({
        'result': 'SUCCESS',
        'data': 'It worked!'
    })
