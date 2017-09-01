#!/usr/bin/env python
# -*- coding: utf-8 -*-

# python script to build cloud formation stacks for building and
# deploying dockerized app via jenkins

import boto3
import jenkins
import requests
import json
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import time
import settings    # our settings.py file

client = boto3.client('cloudformation')
ec2client = boto3.client('ec2')
ssmclient = boto3.client('ssm')
ecrclient = boto3.client('ecr')

# TODO: check that the client can work in this region
#       or, check the aws config template to pick the keyname we use in
#       creation and pass that keyname into the call to create_stack
# - add variables for other hard coded strings
# - break this up into classes for stack creation, repository, stack config
# - logging
# - return the jenkins url and the app url to make manual confirmation easy
# - try a t2.micro for the jenkins stack


ECS_STACK_NAME = settings.ECS_STACK_NAME
ECS_TEMPLATE = settings.ECS_TEMPLATE

# JenkinsStackName = "JenkinsScriptedStack"
#JENKINS_STACK_NAME = "JenkinsScriptedStack"
JENKINS_STACK_NAME = settings.JENKINS_STACK_NAME
# JenkinsTemplate = 'ecs-jenkins-demo.template'
#JENKINS_TEMPLATE = 'ecs-jenkins-demo.template'
JENKINS_TEMPLATE = settings.JENKINS_TEMPLATE
# JenkinsJobTemplate = 'jenkins-job.xml'
#JENKINS_JOB_TEMPLATE = 'jenkins-job.xml'
JENKINS_JOB_TEMPLATE = settings.JENKINS_JOB_TEMPLATE
# JenkinsJobName = "Demo"
# JENKINS_JOB_NaME = "Demo"
JENKINS_JOB_NAME = settings.JENKINS_JOB_NAME

GITHUB_PROJECT = settings.GITHUB_PROJECT
GITHUB_URL = settings.GITHUB_URL

# for Docker
# RepoName = 'scripted-repo'
# DOCKER_REPO_NAME = 'scripted-repo'
DOCKER_REPO_NAME = settings.DOCKER_REPO_NAME

#user = "admin1"
#pwd = "password01!"
#githubUsername = 'slartibaartfast'
#githubPassword = 'Password01!'

JENKINS_USER = settings.JENKINS_USER
JENKINS_PASSWORD = settings.JENKINS_PASSWORD

GITHUB_USERNAME = settings.GITHUB_USERNAME
GITHUB_PASSWORD = settings.GITHUB_PASSWORD


# Runs commands on remote aws linux instances
def execute_ssm_command(commands, instance_ids):
    # The instance must have ssm agent installed!
    # check with aws ssm describe-instance-information
    # output to s3 only?  Maybe go back to paramiko
    response = ssmclient.send_command(
        DocumentName="AWS-RunShellScript", # One of AWS' preconfigured documents
        Parameters={'commands': commands}, # A list of commands
        InstanceIds=[instance_ids] # A list of instance_ids
    )
    return response


# return the instanceid of a running stack
def fetch_jenkins_instanceid(JenkinsStackName):
    # TODO: this should be for any stack name

    response = ec2client.describe_instances(
        Filters=[
            {
                'Name': 'tag-value',
                'Values': [
                    JenkinsStackName,
                ],
            },
            {
                'Name': 'instance-state-name',
                'Values': [
                    'running'
                ]
            },
        ],
    )
    InstanceId = response['Reservations'][0]['Instances'][0]['InstanceId']
    return InstanceId


# return the url for the Jenkins stack
def fetch_jenkins_url(JenkinsStackName):
    # TODO: this should be for any stack
    response = ec2client.describe_instances(
        Filters=[
            {
                'Name': 'tag-value',
                'Values': [
                    JenkinsStackName,
                ]
            },
            {
                'Name': 'instance-state-name',
                'Values': [
                    'running'
                ]
            },
        ],
    )
    jenkinsurl = response['Reservations'][0]['Instances'][0]['PublicDnsName']
    return jenkinsurl


# return the initial admin password from the jenkins server
def fetch_jenkins_pwd(JenkinsStackName):
    commands = ['sudo cat /var/lib/jenkins/secrets/initialAdminPassword']
    instance_ids = fetch_jenkins_instanceid(JenkinsStackName)
    print("instance_ids ", instance_ids)
    response = execute_ssm_command(commands, instance_ids)
    print('initial admin password ', response)
    return response


# create a jenkins user
def create_jenkins_user(instance_ids):
    # on the server...
    # sudo -i
    # echo 'jenkins.model.Jenkins.instance.securityRealm.createAccount("user1", "jive01!")' | java -jar /var/cache/jenkins/war/WEB-INF/jenkins-cli.jar -s "http://localhost:8080/" -auth "admin:$(cat /var/lib/jenkins/secrets/initialAdminPassword)" groovy =

    command = 'sudo echo \'jenkins.model.Jenkins.instance.securityRealm.createAccount(\"{}\", \"{}\")\' | java -jar /var/cache/jenkins/war/WEB-INF/jenkins-cli.jar -s "http://localhost:8080/" -auth "admin:$(cat /var/lib/jenkins/secrets/initialAdminPassword)" groovy ='.format(JENKINS_USER, JENKINS_PASSWORD)
    commands = []
    commands.append(command)

    response = execute_ssm_command(commands, instance_ids)
    return response


# fetch the token from the server
def fetch_user_token(jenkinsUrl, JENKINS_USER, JENKINS_PASSWORD):
    url = 'http://' + jenkinsUrl + '/user/' + JENKINS_USER + '/configure'
    page = requests.get(url, auth=(JENKINS_USER, JENKINS_PASSWORD))
    content = page.content
    soup = BeautifulSoup(content, 'html.parser')
    token = soup.find('input', {'id': 'apiToken'}).get('value')

    return token


# disable web based setup wizard
def disable_jenkins_setup_wizard(instance_ids):
    # not using this atm...it might work on older jenkins versions
    # java -Djenkins.install.runSetupWizard=false -jar /usr/lib/jenkins/jenkins.war
    commands = [
        'java \
        -Djenkins.install.runSetupWizard=false \
        -jar /usr/lib/jenkins/jenkins.war '
        ]

    response = execute_ssm_command(commands, instance_ids)
    return response


# see if a running stack exists
def check_stack_exists(StackName):
    # check for running stacks of StackName
    try:
        response = client.describe_stacks(StackName=StackName)
        if len(response) > 1:
            print('check_stack_exists returned true for ', StackName)
            return 1
    except:
        pass
        print('check_stack_exists returned false for ', StackName)
        return 0


# delete a stack and wait for it to be deleted
def delete_stack(StackName, Waiter):
    # TODO: there should be a better way to do this
    # TODO: call delete_stack_instances ? first so it doesn't fail
    #       when trying to delete draining instances
    # TODO: need to check for dependant stacks & repos, delete them first
    try:
        print('trying to delete the stack', StackName)
        client.delete_stack(StackName=StackName)
        # wait for it
        cf_delete_complete_waiter = client.get_waiter(Waiter)
        cf_delete_complete_waiter.wait(StackName=StackName)
    except:
        print("Failed to delete instance, trying again")
        # didn't drain instances fast enough or something...try again
        client.delete_stack(StackName=StackName)
        # get a waiter and wait for the stack to be deleted
        cf_delete_complete_waiter = client.get_waiter(Waiter)
        cf_delete_complete_waiter.wait(StackName=StackName)
    else:
        # TODO: what's the exception for stack does not exist?
        #       raise an error if delete fails, don't pass
        pass


# helper function, called before running create_stack to check template syntax
def validate_template(Template):
    print('validating template ', Template)
    try:
        with open(Template, 'r') as f:
            client.validate_template(TemplateBody=f.read())
        return 1
    except Exception as e:
        raise


# open the template and build the stack
def create_ecs_stack(StackName, Template):
    # TODO: paramater values should be variables
    # TODO: generate a token?
    # TODO: put this in a try except
    # TODO: how do you set the stack_set_name during stack creation?
    #       Is it the same as the stack name? No.
    #       It dosn't seem to exist at this point.

    # see if the stack already exists
    if check_stack_exists(StackName):
        # the stack exists, delete it
        delete_stack(StackName, 'stack_delete_complete')

    # check syntax of the template for the new stack
    validate_template(Template)

    print("calling create_stack for ", StackName)
    with open(Template, 'r') as f:
        #response = cfclient.validate_template(TemplateBody=f.read())
        response = client.create_stack(
            StackName=StackName,
            TemplateBody=f.read(),
            Parameters=[
                {
                    'ParameterKey': 'KeyName',
                    'ParameterValue': 'stelligent',
                    'UsePreviousValue': False
                },
                {
                    'ParameterKey': 'EcsCluster',
                    'ParameterValue': 'scripted-cluster',
                    'UsePreviousValue': False
                },
                {
                    'ParameterKey': 'AsgMaxSize',
                    'ParameterValue': '2',
                    'UsePreviousValue': False
                },
            ],
            TimeoutInMinutes=5,
            Capabilities=[
                'CAPABILITY_IAM',
            ],
            OnFailure='DELETE',
            Tags=[
                {
                    'Key': 'Name',
                    'Value': 'ECS'
                },
            ],
            ClientRequestToken='token2'
        )

    # get a waiter and wait until create_stack finishes
    # TODO: also check if the stack has completed its config checks
    # is there a waiter for that? yes. EC2.Waiter.InstanceStatusOk
    cf_create_complete_waiter = client.get_waiter('stack_create_complete')
    cf_create_complete_waiter.wait(StackName=StackName)

    print("response ", response)


# create the Jenkins service
def create_jenkins_stack(StackName, Template):
    # see if the stack already exists
    if check_stack_exists(StackName):
        # the stack exists, delete it
        delete_stack(StackName, 'stack_delete_complete')

    # check syntax of the template for the new stack
    validate_template(Template)

    # TODO: put this in a try except
    # aws cloudformation create-stack
    # --template-body file://ecs-jenkins-demo.template
    # --stack-name JenkinsStack
    # --capabilities CAPABILITY_IAM
    # --tags Key=Name,Value=Jenkins
    # --region us-west-2
    # --parameters
    #    ParameterKey=EcsStackName,ParameterValue=EcsClusterStack

    # create the Jenkins stack
    print('creating the Jenkins stack')
    #with open(JenkinsTemplate, 'r') as f:
    with open(Template, 'r') as f:
        response = client.create_stack(
            # StackName=JenkinsStackName,
            StackName=StackName,
            TemplateBody=f.read(),
            Parameters=[
                {
                    'ParameterKey': 'EcsStackName',
                    'ParameterValue': ECS_STACK_NAME,
                    'UsePreviousValue': False
                },
            ],
            TimeoutInMinutes=5,
            Capabilities=[
                'CAPABILITY_IAM',
            ],
            OnFailure='DELETE',
            Tags=[
                {
                    'Key': 'Name',
                    'Value': 'ScriptedJenkins'
                },
            ],
            ClientRequestToken='JenkinsToken1'
        )

    # get a waiter and wait until create_stack finishes
    # TODO: move to own function
    cf_create_complete_waiter = client.get_waiter('stack_create_complete')
    # cf_create_complete_waiter.wait(StackName=JenkinsStackName)
    cf_create_complete_waiter.wait(StackName=StackName)


# configure Jenkins, add a job in the Jenkins stack we created
def configure_jenkins_stack(StackName, JobTemplate):
    # TODO: check to make sure everything is up, see status checks
    #       class EC2.Waiter.InstanceStatusOk
    # TODO: break this up, get constants out

    jenkinsUrl = fetch_jenkins_url(StackName)
    instance_ids = fetch_jenkins_instanceid(StackName)

    print(instance_ids)

    #InstanceIds = []
    #InstanceIds.append('instance_ids')
    cf_status_ok_waiter = ec2client.get_waiter('instance_status_ok')
    cf_status_ok_waiter.wait(InstanceIds=[instance_ids])

    #jenkinsUrl = fetch_jenkins_url(JenkinsStackName)
    #instance_ids = fetch_jenkins_instanceid(JenkinsStackName)

    # wait for aws to finish status checks
    # TODO: see if boto can check this
    #time.sleep(120)
    create_jenkins_user(instance_ids)

    # TODO: need a better waiter
    time.sleep(10)
    token = fetch_user_token(jenkinsUrl, JENKINS_USER, JENKINS_PASSWORD)

    # login to Jenkins
    url = 'http://' + jenkinsUrl
    server = jenkins.Jenkins(
        url=url,
        username=JENKINS_USER,
        password=token
        )

    # install some plugins
    server.install_plugin('git', include_dependencies=True)
    server.install_plugin('github', include_dependencies=True)
    server.install_plugin('amazon-ecr', include_dependencies=True)
    server.install_plugin('docker-build-publish', include_dependencies=True)

    # restart jenkins service
    command = 'service jenkins restart'
    commands = []
    commands.append(command)
    execute_ssm_command(commands, instance_ids)

    # wait 30 seconds for jenkins to restart
    # TODO: check the serivice status using a boto3 waiter
    server.wait_for_normal_op(30)

    # add credentials for a jenkins user to log in to github
    # TODO: clean up hardcoded stirngs in job xml file and this one
    print('calling add credentials')
    add_jenkins_credentials(StackName)

    # update the jenkins job template with the new credentials
    edit_jenkins_job(token, JobTemplate)

    print('Creating Jenkins Job')
    # xml = open(JenkinsJobTemplate).read()
    xml = open(JobTemplate).read()
    #xml = xml % quiet_period
    # server.create_job(JenkinsJobName, xml)
    server.create_job(JENKINS_JOB_NAME, xml)

    # TODO: add github hook
    #       this is in the job config, on a per job basis?


# add a jenkins user to run the job
def add_jenkins_credentials(StackName):
    jenkinsUrl = fetch_jenkins_url(StackName)
    token = fetch_user_token(jenkinsUrl, JENKINS_USER, JENKINS_PASSWORD)
    #print(token)
    #print(JENKINS_USER)

    # get the crumb
    #c = requests.get('http://admin1:a44fb377c91a34777c013e7f8f6e87cb@ec2-54-89-36-223.compute-1.amazonaws.com/crumbIssuer/api/xml/crumbIssuer/api/xml')
    crumbUrl = 'http://' + JENKINS_USER + ':' + token + '@' + jenkinsUrl + '/crumbIssuer/api/xml/crumbIssuer/api/xml'
    c = requests.get(crumbUrl)
    # c = requests.get('http://admin1:a44fb377c91a34777c013e7f8f6e87cb@ec2-54-89-36-223.compute-1.amazonaws.com/crumbIssuer/api/xml/crumbIssuer/api/xml')
    soup = BeautifulSoup(c.text, "html.parser")
    crumb = soup.find('crumb').string
    print('crumbUrl ', crumbUrl)
    print('crumb', crumb)

    # create the credentials
    # url = 'http://admin1:a44fb377c91a34777c013e7f8f6e87cb@' + jenkinsUrl + '/credentials/store/system/domain/_/createCredentials'
    url = 'http://' + JENKINS_USER + ':' + token + '@' + jenkinsUrl + '/credentials/store/system/domain/_/createCredentials'
    print(url)
    # headers = {'Jenkins-Crumb': 'e9e78454ba34da482871de8b5936c26e'}
    headers = {'Jenkins-Crumb': crumb}
    data = {
        '': '0',
        'credentials':{'scope': 'GLOBAL',
        #'id': '85dc44be-a330-4328-af56-7de451f2a786',
        # usually the token and the id are different
        'id': token,
        #'username': 'slartibaartfast',
        'username': GITHUB_USERNAME,
        'password': GITHUB_PASSWORD,
        'description':'Jenkins user for running build jobs from github',
        'stapler-class': 'com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl'}
    }
    payload = {
        'json': json.dumps(data),
        'Submit': "OK",
    }
    #r = requests.post(url, data=payload, headers=headers, auth=(JENKINS_USER, token))
    r = requests.post(url, data=payload, headers=headers)
    print(r)
    return token


# edit the job template to use our new token for github access
def edit_jenkins_job(token, JobTemplate):
    # <hudson.plugins.git.UserRemoteConfig>
    #    <url> the github repo.git
    #    <credentialsId> a valid jenkins credentialsId
    tree = ET.parse(JobTemplate)
    root = tree.getroot()

    # fetch the xml fields we want to update
    url = root.findall('.//hudson.plugins.git.UserRemoteConfig/url')
    credentialsId = root.findall('.//hudson.plugins.git.UserRemoteConfig/credentialsId')

    # set new values for url and credentialId
    url[0].text = GITHUB_URL
    credentialIds[0].text = token

    # save the changes to the template file that got passed in
    tree.write(JobTemplate)


# create a private docker registry in ecr
def create_ecr_repo(RepoName):
    # TODO: see if this exists before creating it
    print('reponame ', RepoName)
    response = ecrclient.create_repository(repositoryName=RepoName)
    repositoryUri = response['repository']['repositoryUri']
    # registryId = response['repository']['registryId']
    return repositoryUri


# get a 24hr login to a repository
def fetch_docker_login(RegistryId):
    response = ecrclient.get_authorization_token(
        registryIds=[RegistryId] # a list of registry ids
        )

# call our steps
def do_steps():
    # create the ecs stack
    print('calling create_ecs_stack')
    create_ecs_stack(StackName=ECS_STACK_NAME, Template=ECS_TEMPLATE)

    # create the Jenkins stack
    print('calling create_jenkins_stack')
    # create_jenkins_stack(StackName=JenkinsStackName, Template=JenkinsTemplate)
    create_jenkins_stack(StackName=JENKINS_STACK_NAME, Template=JENKINS_TEMPLATE)

    # create the aws registry for docker
    print('calling create_ecr_repo')
    create_ecr_repo(RepoName=DOCKER_REPO_NAME)

    # configure jenkins
    print('configuring Jenkins')
    configure_jenkins_stack(
        # StackName=JenkinsStackName,
        StackName=JENKINS_STACK_NAME,
        # JobTemplate=JenkinsJobTemplate
        JobTemplate=JENKINS_JOB_TEMPLATE
        )

    print('finished')

    # create a subdomain and load ballancer?

    # run tests
    #run_tests(url='http://stelligent.tomrota.com')


if __name__ == "__main__":
    do_steps()
