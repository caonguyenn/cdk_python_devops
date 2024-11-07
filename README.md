# Welcome to your CDK Python project!

This is a project used to deploy Tomcat server using CDK development with Python.

This project is set up like a standard Python project. We should create virtualenv for our project (virtualenv allows you to avoid installing Python packages globally by making an isolated python environment).

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

Create a CloudFormation stack with the name CDKToolkit by usng bootstrap command

```
$ cdk bootstrap
```

We support to deploy resources on multiple environment like dev, test, prod. So, need to specify the env context when deploying (--context env=dev, test, prod).
Also can change the capacity of ASG and instance type in `parameters.yaml` file to achieve your expected reources

```
dev:
  instance_type: "t2.micro"
  min_capacity: 1
  max_capacity: 2
  desired_capacity: 1
```
At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth --context env=<env>
```

Now, you can deploy resources using deploy command (remember to specify env context)

```
$ cdk deploy --context env=<env>
```


## Useful commands

 * `cdk ls --context env=<env>`          list all stacks in the app
 * `cdk synth --context env=<env>`       emits the synthesized CloudFormation template
 * `cdk deploy --context env=<env>`      deploy this stack to your default AWS account/region
 * `cdk diff --context env=<env>`        compare deployed stack with current state
 * `cdk destroy --context env=<env>`     destriy current state

Enjoy!
