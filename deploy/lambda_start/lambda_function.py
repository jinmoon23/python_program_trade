import boto3

def lambda_handler(event, context):
    ec2 = boto3.client('ec2', region_name='ap-southeast-2')
    instance_id = 'i-0eee1e49b27604b17'
    
    ec2.start_instances(InstanceIds=[instance_id])
    
    return {
        'statusCode': 200,
        'body': f'Started instance {instance_id}'
    }
