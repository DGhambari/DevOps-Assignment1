import boto3
import logging
from datetime import datetime

date = datetime.now().strftime("%Y_%m_%d-%I:%M:%S_%p")
logging.basicConfig(filename=f'ec2log_{date}.txt', format='%(asctime)s %(message)s')

IMG_URL="http://devops.witdemo.net/assign1.jpg"
USER_DATA="""yum update -y && \
yum install httpd -y && \
enable httpd && \
systemctl start httpd
"""

ec2 = boto3.resource('ec2')

# Create new instance
new_instance = ec2.create_instances(
    ImageId='ami-033b95fb8079dc481',
    MinCount=1,
    MaxCount=1,
    InstanceType='t2.nano',

    # Security key
    KeyName='aws_key',

    # Security group id
    SecurityGroupIds=[
        'sg-04c8b4ea3e9590e69',
    ],

    # Updates the ec2 instance and installs Apache for static web hosting
    UserData=USER_DATA,
                
    TagSpecifications=[
        {
            'ResourceType': 'instance',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': 'My web server'
                },
            ],
        },
    ],
),



"""
for instance in new_instance:
    print(f'EC2 instance {instance.id}" information:')
    print(f'Instance state: {instance.state["Name"]}')
    print(f'Instance AMI: {instance.image.id}')
    print(f'Instance platform: {instance.platform}')
    print(f'Instance type: "{instance.instance_type}')
    print(f'Piblic IPv4 address: {instance.public_ip_address}')
    print('-'*60)
"""