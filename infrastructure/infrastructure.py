from aws_cdk import (
    Stack,
    Tags,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_autoscaling as autoscaling,
    aws_elasticloadbalancingv2 as elbv2,
    aws_iam as iam,
    aws_s3 as s3,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as cp_actions,
    aws_codebuild as codebuild,
    aws_codedeploy as codedeploy,
    aws_kms as kms,
    CfnOutput
)
import yaml
from constructs import Construct
from constants import Network, Account, LaunchTemplate, Roles, Email, Project, Github

class InfrastructureStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, environment: str, **kwargs) -> None:
        """
        environment (str): dev, test, prod
        """
        super().__init__(scope, construct_id, **kwargs)

        env = environment

         # Load parameters from YAML file
        with open("parameters.yaml", "r") as file:
            params = yaml.safe_load(file)

        instance_config = params.get(env)

        # Security Group for EC2 instances and Load Balancer
        security_group = ec2.SecurityGroup.from_security_group_id(self, "SG", Network.SG_ID,
            mutable=False)
        
        # Subnets
        subnet_ids = [Network.SUBNET_ID_1, Network.SUBNET_ID_2, Network.SUBNET_ID_3]
        subnets = [ec2.Subnet.from_subnet_id(self, f"Subnet{i}", subnet_id) for i, subnet_id in enumerate(subnet_ids)]

        # Vpc
        vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_id=Network.VPC_ID)

        removal_policy = RemovalPolicy.RETAIN if env=="prod" else RemovalPolicy.DESTROY
        auto_delete_objects = False if env == "prod" else True

        # Create Log bucket and ServerAccessLog bucket for ALB
        server_access_log_bucket = s3.Bucket(self, "ServerAccessLogsBucket",
            bucket_name=f"{Github.OWNER}-alb-serveraccess-log-{env}",
            removal_policy=removal_policy,
            auto_delete_objects=auto_delete_objects,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True
        )

        log_bucket = s3.Bucket(self, "ALBAccessLogsBucket",
            bucket_name=f"{Github.OWNER}-alb-log-{env}",
            removal_policy=removal_policy,
            auto_delete_objects=auto_delete_objects,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            server_access_logs_bucket=server_access_log_bucket
        )

        # Create instance s3 bucket
        instance_bucket = s3.Bucket(self, "InstanceBucket",
            bucket_name=f"{Github.OWNER}-instance-{env}-bucket",
            removal_policy=removal_policy,
            auto_delete_objects=auto_delete_objects,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            server_access_logs_bucket=server_access_log_bucket
        )


        # Create the Application Load Balancer
        alb = elbv2.ApplicationLoadBalancer(
            self, 
            "LoadBalancer",
            load_balancer_name=f"ALB-{Project.PROJECT_NAME}-{env}",
            vpc=vpc,
            internet_facing=True,
            security_group=security_group,
            vpc_subnets=ec2.SubnetSelection(subnets=subnets)
        )

        alb.log_access_logs(log_bucket)

        # Create the Target Group
        target_group = elbv2.ApplicationTargetGroup(
            self, 
            "TargetGroup",
            target_group_name=f"TargetGR-{env}",
            vpc=vpc,
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.INSTANCE,
            health_check=elbv2.HealthCheck(path="/"),
        )

        # Add listener to Load Balancer
        alb.add_listener(
            "Listener",
            port=80,
            default_target_groups=[target_group]
        )

        instance_role = iam.Role.from_role_arn(self, "InstanceRole", 
            role_arn=Roles.AmazonEC2RoleforAWSCodeDeploy)

        # Create an SNS topic for Auto Scaling notifications
        sending_mail_toppic = sns.Topic(self, "SendingEmailTopic", enforce_ssl=True)
        sending_mail_toppic.add_subscription(subs.EmailSubscription(Email.email))

        # Enforce SSL for publishers
        sending_mail_toppic.add_to_resource_policy(
            iam.PolicyStatement(  # Use iam.PolicyStatement instead of sns.PolicyStatement
                actions=["sns:Publish"],
                resources=[sending_mail_toppic.topic_arn],
                effect=iam.Effect.ALLOW,
                principals=[iam.ArnPrincipal("*")],  # Allow any principal
                conditions={
                    "Bool": {"aws:SecureTransport": "true"}  # Enforce SSL
                }
            )
        )

        notification_configuration = autoscaling.NotificationConfiguration(
            topic=sending_mail_toppic
        )

        with open("userdata.sh", "r") as userdata_file:
            userdata_script = userdata_file.read()

        userdata = ec2.UserData.for_linux()
        userdata.add_commands(userdata_script)
        userdata.add_s3_download_command(
            bucket=instance_bucket,
            bucket_key="target/myapp",   # S3 key for the file
            local_file="/opt/tomcat/webapps/"  # Path on the EC2 instance
        )
        userdata.add_commands("exit 0")

        # Define an Auto Scaling Group
        # [disable-awslint:ref-via-interface]
        asg = autoscaling.AutoScalingGroup(
            self, 
            "AutoScalingGroup",
            auto_scaling_group_name=f"ASG-{Project.PROJECT_NAME}-{env}",
            vpc=vpc,
            instance_type=ec2.InstanceType(instance_config["instance_type"]),
            machine_image=ec2.MachineImage.generic_linux({
                Account.REGION: LaunchTemplate.AMI
            }),
            min_capacity=instance_config["min_capacity"],
            max_capacity=instance_config["max_capacity"],
            desired_capacity=instance_config["desired_capacity"],
            vpc_subnets=ec2.SubnetSelection(subnets=subnets),
            security_group=security_group,
            user_data=userdata,
            role=instance_role,
            notifications=[notification_configuration],
            block_devices=[autoscaling.BlockDevice(
                device_name="/dev/xvda",
                volume=autoscaling.BlockDeviceVolume.ebs(
                    volume_size=8,
                    encrypted=True
                )
            )]
        )
        Tags.of(asg).add("Name", f"{Project.PROJECT_NAME}-{env}-Instance")

        asg.scale_on_cpu_utilization("CpuScaling", target_utilization_percent=75)
        asg.attach_to_application_target_group(target_group)

        ############################################################################################
        ## Pipeline
        ############################################################################################

        # Define an access logs bucket
        access_logs_bucket = s3.Bucket(self, "AccessLogsBucket",
            bucket_name=f"{Github.OWNER}-pipeline-serveraccess-log-{env}",
            enforce_ssl=True,
            removal_policy=removal_policy,
            auto_delete_objects=auto_delete_objects)

        # Define the artifacts bucket with logging enabled
        artifacts_bucket = s3.Bucket(self, "ArtifactsBucket",
            server_access_logs_bucket=access_logs_bucket,
            auto_delete_objects=auto_delete_objects,
            removal_policy=removal_policy,
            bucket_name=f"{Github.OWNER}-pipeline-log-{env}", enforce_ssl=True)
        # CodePipeline
        pipeline = codepipeline.Pipeline(self, "Pipeline",
            pipeline_name=f"{Project.PROJECT_NAME}-{env}-Pipeline",
            artifact_bucket=artifacts_bucket
        )
        
        # Source Stage
        source_output = codepipeline.Artifact()
        source_action = cp_actions.CodeStarConnectionsSourceAction(
            action_name=f"GitHub-Source-{env}",
            owner=Github.OWNER,
            repo=Github.REPO,
            branch=env,
            connection_arn=Github.CONNECTION_ARN,
            output=source_output,
            trigger_on_push=True
        )
        pipeline.add_stage(
            stage_name="Source",
            actions=[source_action]
        )

        # CodeBuild Stage
        kms_key = kms.Key(self, "CodeBuildKey", enable_key_rotation=True)
        build_output = codepipeline.Artifact()
        build_project = codebuild.PipelineProject(self, "BuildProject",
            project_name=f"{Project.PROJECT_NAME}-BuildProject-{env}",
            encryption_key=kms_key,
            role=iam.Role.from_role_arn(self, "CodebuildRole", role_arn=Roles.CodebuildRole))

        build_action = cp_actions.CodeBuildAction(
            action_name="Build",
            project=build_project,
            input=source_output,
            outputs=[build_output],
            environment_variables={
                "INSTANCE_BUCKET_NAME": codebuild.BuildEnvironmentVariable(value=instance_bucket.bucket_name)
            })

        pipeline.add_stage(
            stage_name="Build",
            actions=[build_action]
        )

        # CodeDeploy Application and Deployment Group
        codedeploy_app = codedeploy.ServerApplication(self, "CodeDeployApp",
            application_name=f"{Project.PROJECT_NAME}-DeployApplication")

        deployment_config = codedeploy.ServerDeploymentConfig.ALL_AT_ONCE if env == "dev" else codedeploy.ServerDeploymentConfig.HALF_AT_A_TIME

        codedeploy_deployment_group = codedeploy.ServerDeploymentGroup(self, "CodeDeployDeploymentGroup",
            application=codedeploy_app,
            deployment_group_name=f"{Project.PROJECT_NAME}-DeploymentGroup-{env}",
            auto_scaling_groups=[asg],
            load_balancer=codedeploy.LoadBalancer.application(target_group),
            deployment_config=deployment_config)
        
        # Deployment Stage
        deploy_action = cp_actions.CodeDeployServerDeployAction(
            action_name="Deploy",
            input=build_output,
            deployment_group=codedeploy_deployment_group
        )

        pipeline.add_stage(
            stage_name="Deploy",
            actions=[deploy_action]
        )

        pipeline.notify_on(
            "FailedPipelineNotifications",
            sending_mail_toppic,
            events=[
                codepipeline.PipelineNotificationEvents.PIPELINE_EXECUTION_FAILED
            ]
        )