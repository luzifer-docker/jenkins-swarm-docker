# jenkins-swarm-docker

This repository contains a **Dockerfile** for a [Jenkins](http://jenkins-ci.org/) [Swarm-Slave](https://wiki.jenkins-ci.org/display/JENKINS/Swarm+Plugin) with [Docker](https://www.docker.com/) support to control a [CoreOS](https://coreos.com/) slave and let all the things run on CoreOS Docker.

## Usage

1. Set up a Jenkins Master (for example use [luzifer/jenkins](https://registry.hub.docker.com/u/luzifer/jenkins/))
2. Create an [AWS](http://aws.amazon.com/) CloudFormation stack for your CoreOS build machines  
   (An example is available in [this respository](https://github.com/luzifer-docker/jenkins-swarm-docker))
3. Fill in your masters data into the python version of the stack template
4. Let the python file generate a CloudFormation JSON: `python sample.py > sample.json`
5. Boot the stack using AWS CloudFormation
