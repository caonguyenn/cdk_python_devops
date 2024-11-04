from aws_cdk import (
    Stack,
    Fn,
    Tags,
    RemovalPolicy,
    aws_iam as iam,
    aws_autoscaling as autoscaling,
    aws_elasticloadbalancingv2 as elbv2,
    aws_s3 as s3,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as cp_actions,
    aws_codebuild as codebuild,
    aws_codedeploy as codedeploy,
    aws_kms as kms,
    aws_events as events,
    aws_events_targets as targets,
    CfnOutput
)
from constructs import Construct
from constants import Project, Github


class InfrasPipelineStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, environment: str, **kwargs) -> None:
        """
        environment (str): dev, test, prod
        """
        super().__init__(scope, construct_id, **kwargs)

        env = environment

        asg_name = Fn.import_value(f"ASG-{Project.PROJECT_NAME}-{env}")
        target_group_arn = Fn.import_value(f"TGarn-{Project.PROJECT_NAME}-{env}")
        instance_bucket_name = Fn.import_value(f"Instance-bucket-{env}")
        sending_mail_toppic_arn = Fn.import_value(f"SNS-mailsending-arn-{env}")
        cdk_pipeline_arn =  Fn.import_value(f"CDKPipeline-arn-{env}")
        sending_mail_toppic_arn = Fn.import_value(f"SNS-mailsending-arn-{env}")

        cdk_pipeline = codepipeline.Pipeline.from_pipeline_arn(self, "ImportedPipeline",
                pipeline_arn=cdk_pipeline_arn)
        asg = autoscaling.AutoScalingGroup.from_auto_scaling_group_name(self, "ImportedASG", asg_name)
        target_group = elbv2.ApplicationTargetGroup.from_target_group_attributes(self, "ImportedTargetGroup",
            target_group_arn=target_group_arn)
        instance_bucket = s3.Bucket.from_bucket_name(self, "ImportedLogBucket", instance_bucket_name)
        sending_mail_toppic = sns.Topic.from_topic_arn(self, "ImportedTopic", sending_mail_toppic_arn)

        removal_policy = RemovalPolicy.RETAIN if env=="prod" else RemovalPolicy.DESTROY
        auto_delete_objects = False if env == "prod" else True

        trigger_topic = sns.Topic(self, f"PipelineTriggerTopic-{env}")

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

        cdk_pipeline.notify_on(
            "PipelineNotifications",
            trigger_topic,
            events=[
                codepipeline.PipelineNotificationEvents.PIPELINE_EXECUTION_SUCCEEDED
            ]
        )

        pipeline.notify_on(
            "FailedPipelineNotifications",
            sending_mail_toppic,
            events=[
                codepipeline.PipelineNotificationEvents.PIPELINE_EXECUTION_FAILED
            ]
        )

        # Create event to trigger infars pipeline
        rule = events.Rule(self, "TriggerPipelineFromSNS",
            event_pattern={
                "source": ["aws.sns"],
                "detail_type": ["SNS Topic Notification"],
                "resources": [trigger_topic.topic_arn]
            }
        )

        rule.add_target(targets.CodePipeline(pipeline))
        
        # Source Stage
        source_output = codepipeline.Artifact()
        source_action = cp_actions.CodeStarConnectionsSourceAction(
            action_name=f"GitHub-Source-{env}",
            owner=Github.OWNER,
            repo=Github.REPO,
            branch=env,
            connection_arn=Github.CONNECTION_ARN,
            output=source_output,
            trigger_on_push=False
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
            encryption_key=kms_key)

        build_action = cp_actions.CodeBuildAction(
            action_name="Build",
            project=build_project,
            input=source_output,
            outputs=[build_output],
            environment_variables={
                "INSTANCE_BUCKET_NAME": codebuild.BuildEnvironmentVariable(value=instance_bucket_name)
            }
        )
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
