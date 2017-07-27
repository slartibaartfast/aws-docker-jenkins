hello-world
===========

[![Deploy to Docker Cloud](https://files.cloud.docker.com/images/deploy-to-dockercloud.svg)](https://cloud.docker.com/stack/deploy/)

Sample docker image to test docker deployments

## Running locally

Build and run using Docker Compose:

	$ git clone https://github.com/docker/dockercloud-hello-world
	$ cd dockercloud-hello-world
	$ docker-compose up


## Deploying to Docker Cloud

[Install the Docker Cloud CLI](https://docs.docker.com/docker-cloud/tutorials/installing-cli/)

	$ docker login
	$ docker-cloud stack up

## Deploying to AWS

[See the tutorial](http://docs.aws.amazon.com/AWSGettingStartedContinuousDeliveryPipeline/latest/GettingStarted/CICD_Jenkins_Pipeline.html)

[Download the jenkins cli](http://ec2-107-21-81-252.compute-1.amazonaws.com/jnlpJars/jenkins-cli.jar)

  A build is kicked off upon a checkin to this repo

	To run a build command manually, use the Jenkins CLI

	$ java -jar jenkins-cli.jar -s http://ec2-107-21-81-252.compute-1.amazonaws.com/ build Stelligent

	TODO: add a build command example
