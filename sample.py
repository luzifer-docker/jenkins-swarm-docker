__author__ = 'luzifer'

from troposphere import Template
from troposphere import autoscaling, ec2, Ref, Base64
from troposphere.policies import AutoScalingRollingUpdate, UpdatePolicy

latest_ami = 'ami-52d29925' # CoreOS Alpha 752.1.0
instance_type = 'm3.medium'
ssh_key_name = 'mykey'
availability_zones = ['eu-west-1c']

jenkins = {
  'master': 'http://my.jenkins.example.com/',
  'username': 'myuser',
  'password': 'mypass',
  'labels': 'docker',
  'executors': 2,
}

cloud_config = '''#cloud-config

ssh_authorized_keys:
  - [your ssh key here]

write_files:
  - path: /root/.dockercfg
    owner: root:root
    permissions: 0644
    content: |
      {{
        "https://index.docker.io/v1/": {{
          "auth": "mypassword",
          "email": "mail@example.com"
        }}
      }}

coreos:
  units:
    - name: format-ephemeral.service
      runtime: true
      command: start
      content: |
        [Unit]
        Description=Format the EBS volume

        [Service]
        Type=oneshot
        RemainAfterExit=yes
        ExecStart=/usr/sbin/wipefs -f /dev/xvdd
        ExecStart=/usr/sbin/mkfs.btrfs -f /dev/xvdd
    - name: var-lib-docker.mount
      command: start
      content: |
        [Unit]
        Description=Mount ephemeral to /var/lib/docker
        Requires=format-ephemeral.service
        After=format-ephemeral.service
        Before=docker.service

        [Mount]
        What=/dev/xvdd
        Where=/var/lib/docker
        Type=btrfs
    - name: jenkins-swarm.service
      command: start
      content: |
        [Unit]
        Description=Jenkins Swarm Slave
        Author=Knut Ahlers
        After=docker.service

        [Service]
        Restart=always
        ExecStartPre=mkdir -p /home/jenkins
        ExecStartPre=/usr/bin/docker pull luzifer/jenkins-swarm-docker
        ExecStartPre=-/usr/bin/docker rm -f jenkins_slave
        ExecStart=/usr/bin/docker run --name=jenkins_slave -v /home/jenkins:/home/jenkins \
        -v /root/.dockercfg:/home/jenkins/.dockercfg \
        -v /var/run/docker.sock:/var/run/docker.sock luzifer/jenkins-swarm-docker \
        -master "{master}" -executors {executors} -username "{username}" -password "{password}" -labels "{labels}"
        ExecStop=/usr/bin/docker rm -f jenkins_slave
'''.format(**jenkins)

template = Template()

security_group = template.add_resource(ec2.SecurityGroup(
    'InstanceSecurityGroup',
    GroupDescription='Enable SSH access on the configured port',
    SecurityGroupIngress=[
        {"IpProtocol": "icmp", "FromPort": "-1", "ToPort": "-1", "CidrIp": "0.0.0.0/0"},
        {"IpProtocol": "tcp", "FromPort": "22", "ToPort": "22", "CidrIp": "0.0.0.0/0"}
    ]
))

launch_config = template.add_resource(autoscaling.LaunchConfiguration(
    'LaunchConfig',
    ImageId=latest_ami,
    SecurityGroups=[Ref(security_group)],
    InstanceType=instance_type,
    KeyName=ssh_key_name,
    SpotPrice='0.02',
    BlockDeviceMappings=[
        {
            "DeviceName": "/dev/xvdd",
            "Ebs": {
              "VolumeSize": "50",
              "VolumeType": "gp2",
            }
        }
    ],
    UserData=Base64(cloud_config),
))

asg = template.add_resource(autoscaling.AutoScalingGroup(
    'JenkinsSlaveGroup',
    AvailabilityZones=availability_zones,
    LaunchConfigurationName=Ref(launch_config),
    HealthCheckType="EC2",
    HealthCheckGracePeriod=180,
    Cooldown=300,
    DesiredCapacity=1,
    MinSize=0,
    MaxSize=1,
    UpdatePolicy=UpdatePolicy(
        AutoScalingRollingUpdate=AutoScalingRollingUpdate(
        MinInstancesInService=str(0),
        MaxBatchSize='1',
        PauseTime='PT10M'
    )),
))

print template.to_json()
