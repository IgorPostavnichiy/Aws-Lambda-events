import boto3

def lambda_handler(event, context):
    # Проверка, является ли событие запуском или завершением экземпляра EC2
    if event['detail-type'] == 'EC2 Instance State-change Notification':
        instance_id = event['detail']['instance-id']
        state = event['detail']['state']
        
        if state == 'terminated':
            # Получение списка объектов в S3-ведре
            s3 = boto3.resource('s3')
            bucket_name = 'your_bucket_name'  # Замените на имя вашего S3-ведра
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

    return {
        'statusCode': 200,
        'body': 'Success'
    }
