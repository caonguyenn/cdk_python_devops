from strenum import StrEnum

class Network(StrEnum):
    VPC_ID = "vpc-0b6082814d01a349a"
    SG_ID = "sg-0e314fa515c63fef7"
    SUBNET_ID_1 = "subnet-0f0ef9334c7eab9dc"
    SUBNET_ID_2 = "subnet-004174f548f070dfa"
    SUBNET_ID_3 = "subnet-071b7789828788114"

class LaunchTemplate(StrEnum):
    AMI = "ami-047126e50991d067b"

class Account(StrEnum):
    ACCOUNT_ID = "730335432746"
    REGION = "ap-southeast-1"

class Roles(StrEnum):
    AmazonEC2RoleforAWSCodeDeploy = "arn:aws:iam::730335432746:role/AmazonEC2RoleforAWSCodeDeploy"
    CodeDeployServiceRoleForEC2 = "arn:aws:iam::730335432746:role/CodeDeployServiceRoleForEC2"
    CodebuildRole = "arn:aws:iam::730335432746:role/service-role/codebuild-Tomcatdevbuild-service-role"

class Email(StrEnum):
    email = "nguyentancaonguyen@gmail.com"

class Project(StrEnum):
    PROJECT_NAME = "Tomcat"

class Github(StrEnum):
    OWNER = "caonguyenn"
    REPO = "cdk_python_devops"
    CONNECTION_ARN = "arn:aws:codeconnections:ap-southeast-1:730335432746:connection/6d989b7d-c1d4-42a0-9111-5db7485fc10e"
