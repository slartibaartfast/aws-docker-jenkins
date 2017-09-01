#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os.path import join, dirname
from dotenv import load_dotenv
import os

dotenv_path = join(dirname(__file__), 'aws-docker-jenkins.env')
load_dotenv(dotenv_path)

# global variables  (note: some are hardcoded into jenkins-job.xml)
# for Docker
DOCKER_REPO_NAME = 'scripted-repo'

# for cloud formation cluster stack
ECS_STACK_NAME = 'EcsScriptedStack'
ECS_TEMPLATE = 'ecs-cluster.template'

# for jenkins stack
JENKINS_STACK_NAME = "JenkinsScriptedStack"
JENKINS_TEMPLATE = 'ecs-jenkins-demo.template'

# for Jenkins job configuration
JENKINS_JOB_TEMPLATE = 'jenkins-job.xml'
JENKINS_JOB_NAME = "Demo"
GITHUB_PROJECT = "https://github.com/slartibaartfast/aws-docker-jenkins/"
GITHUB_URL = "https://github.com/slartibaartfast/aws-docker-jenkins.git"

# from a .env file, aws-docker-jenkins.env in this case
JENKINS_USER = os.environ.get("JENKINS_USER")
JENKINS_PASSWORD = os.environ.get("JENKINS_PASSWORD")
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME")
GITHUB_PASSWORD = os.environ.get("GITHUB_PASSWORD")
