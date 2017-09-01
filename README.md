This is for creating an infrastructure on AWS used for building and deploying a web app.

===========

## Running locally

Build and run using Docker Compose:

	$ git clone https://github.com/docker/dockercloud-hello-world
	$ cd dockercloud-hello-world
	$ docker-compose up


## Deploying to AWS

[See the tutorial](http://docs.aws.amazon.com/AWSGettingStartedContinuousDeliveryPipeline/latest/GettingStarted/CICD_Jenkins_Pipeline.html) for a description of the AWS environment.

A build is kicked off upon a checkin to this repo.


## Deploying to Docker Cloud

[Install the Docker Cloud CLI](https://docs.docker.com/docker-cloud/tutorials/installing-cli/)

	$ docker login
	$ docker-cloud stack up

[![Deploy to Docker Cloud](https://files.cloud.docker.com/images/deploy-to-dockercloud.svg)](https://cloud.docker.com/stack/deploy/)

Sample docker image to test docker deployments
