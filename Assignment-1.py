import boto3
import logging
import subprocess
import webbrowser
import wget
import time
from datetime import datetime

# Variable declarations
ec2 = boto3.resource('ec2')
s3 = boto3.resource("s3")
aws_key = "aws_key.pem"
s3_client = boto3.client('s3')
instance_list = []
image_url="http://devops.witdemo.net/assign1.jpg"
date = datetime.now().strftime("%Y_%m_%d-%I:%M:%S_%p")
short_date = datetime.now().strftime("%Y-%m-%d-%I%M%S")
bucket_name = f"devops-bucket1-{short_date}"
# logging.basicConfig(filename=f'ec2log_{date}.txt', format='%(asctime)s %(message)s')
user_data = """#!/bin/bash
yum update -y
yum install httpd -y
systemctl enable httpd
systemctl start httpd
"""

# Create new instance
new_instance = ec2.create_instances(
    ImageId='ami-0c02fb55956c7d316',
    MinCount=1,
    MaxCount=1,
    InstanceType='t2.nano',

    # Security key
    KeyName=aws_key,

    # Security group id
    SecurityGroupIds=['sg-04c8b4ea3e9590e69'],

    # Updates the ec2 instance and installs Apache for static web hosting
    UserData=user_data,
                
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

print('*'*40)
print("\nCreating instance\n")
print('*'*40)

# Get list of instance ids
time.sleep(2)
for instance in ec2.instances.all():
    if (str(instance.state["Name"]).lower() == ("pending" or "running")):
        instance_list.append(instance)

# Wait for the instance to start up
print("\nWaiting for instance to start up\n")
print('*'*40)
instance_list[-1].wait_until_running()

# Reload instance
print("\nReloading instance\n")
print('*'*40)
instance_list[-1].reload()

# Print instance ip
public_ip = instance_list[-1].public_ip_address
try:
    print(f'\nEC2 instance {instance_list[-1].id}" information:')
    print(f'Instance state: {instance_list[-1].state["Name"]}')
    print(f'Public IPv4 address: {instance_list[-1].public_ip_address}\n')
except:
    print(f"Problem acquiring the ip address\n")
print('*'*40)
print('\n')

# Downloading the image
image_name = wget.download(image_url) 
s3_image_name = image_name.replace(" ", "+")
print(f'\nImage Successfully Downloaded: {image_name}\n')
print('*'*40)

# Create s3 bucket 
bucket_name=f"devops-bucket1-{short_date}"
try:
    response = s3.create_bucket(Bucket=bucket_name)
    print(f"\nS3 bucket details: \n{response}\n")
    print('*'*40)
except Exception as error:
    print (error)

# Setting the bucket to be publicly readable
bucket = s3.Bucket(bucket_name)
bucket.Acl().put(ACL='public-read')

# Create html page and add image and metadata to it
try:
    with open("index.html", "w") as f:
        f.write(f"<!doctype html>\n")
        f.write(f"<html lang='en'>\n")
        f.write(f"<p>\n")
        f.write(f"\tEC2 instance {instance_list[-1].id} information:\n")
        f.write(f"\tInstance state: {instance_list[-1].state['Name']}\n")
        f.write(f"\tPublic IPv4 address: {instance_list[-1].public_ip_address}\n")
        f.write(f"</p>\n")
        f.write(f"\tHere is an image that I have stored on S3: \n<br>\n")
        f.write(f"\t<img src=https://{bucket_name}.s3.amazonaws.com/{s3_image_name}>\n")
        f.write(f"</html>")
        f.close()
    print(f"\nHtml file created\n")
    print('*'*40)
except Exception as error:
    print (error)

# Create a script to run commands on the ec2 instance
try:
    with open("ssh_script.sh", "w") as f:
        f.write(f"sudo chmod 777 monitor.sh\n")
        f.write(f"sudo ./monitor.sh\n")
        f.write(f"echo 'This instance is running in availability zone:' >> metadata.html\n")
        f.write(f"curl http://169.254.169.254/latest/meta-data/placement/availability-zone >> metadata.html\n")
        f.write(f"echo '<hr>The instance ID is: ' >> metadata.html\n")
        f.write(f"curl http://169.254.169.254/latest/meta-data/instance-id >> metadata.html\n")
        f.write(f"echo '<hr>The instance type is: ' >> metadata.html\n")
        f.write(f"curl http://169.254.169.254/latest/meta-data/instance-type >> metadata.html\n")
        f.close()
    print(f"\nSSH script created\n")
    print('*'*40)
except Exception as error:
    print (error)

# Upload image and html page to the S3 bucket
def upload_file(file_name, content_type):
    s3_client = boto3.client('s3')
    try:
        s3_client.upload_file(
            Filename=file_name, 
            Bucket=bucket_name, 
            Key=file_name, 
            ExtraArgs={'ACL': 'public-read', 'ContentType': content_type}
        )
        print(f"\nSuccessfully uploaded {file_name}\n")
        print('*'*40)
    except Exception as error:
        print (error)

upload_file(image_name, "image/jpeg")
upload_file('index.html', "text/html")

# Define the website configuration
website_configuration = {'IndexDocument': {'Suffix': 'index.html'}}

# Set the website configuration
try:
    s3_client.put_bucket_website(Bucket=bucket_name, WebsiteConfiguration=website_configuration)
except Exception as error:
    print (error)

# Copying our html and monitor.sh files to the ec2 instance, creating a metadata page and 
# adding some data to it
ssh = f"ssh -o StrictHostKeyChecking=no -i {aws_key} ec2-user@{public_ip}"
cmd1 = f"scp -o StrictHostKeyChecking=no -i {aws_key} index.html monitor.sh ssh_script.sh ec2-user@{public_ip}:."
cmd2 = f"{ssh} 'chmod 700 ssh_script.sh'"
cmd3 = f"{ssh} 'sudo ./monitor.sh'"
cmd4 = f"{ssh} 'sudo ./ssh_script.sh'"
cmd5 = f"{ssh} 'sudo cp index.html /var/www/html/index.html'"
cmd6 = f"{ssh} 'sudo cp metadata.html /var/www/html/metadata.html'"

shell_commands = [cmd1, cmd2, cmd3, cmd4, cmd5, cmd6] 

# Sometimes the ssh commands fail to execute so we attempt to run the problematic ones 3 times
def run_ssh_cmd(cmd_to_run):
    i = 0
    for i in range (0,3):
        try:
            sshcode = subprocess.check_output(cmd_to_run, shell=True)
            if sshcode is not None:
                print(f"\nCommand {cmd_to_run} ran successfully\n")
                print('*'*40)
                break
            else:
                print(f"Exit code: {sshcode}")
                continue
        except Exception as error:
            print(error)
            print(f"Number of attempts: {i+1}\n")
            time.sleep(1)
            print('*'*40)
            
for cmd in shell_commands:
    run_ssh_cmd(cmd)

# When the image is uploaded to the browser, open a new browser tab to display it.
# Need to change this to display the webpage that has the image in it
try:
    webbrowser.open_new_tab(f"http://{public_ip}")
    webbrowser.open_new_tab(f"http://{bucket_name}.s3-website-us-east-1.amazonaws.com")
    webbrowser.open_new_tab(f"http://{public_ip}/metadata.html")
    webbrowser.open_new_tab(f"http://{public_ip}/index.html")
except Exception as error:
    print (error)

# Retrieve the website config
try:
    print(f"\nWebsite configuration: \n")
    print(s3_client.get_bucket_website(Bucket=bucket_name))
    print('*'*40)
except Exception as error:
    print (error)