from aws_cdk import (
    # Duration,
    Stack,
    RemovalPolicy,
    Stage,
    aws_s3 as s3,
    aws_sns as sns,
    Environment,
    pipelines,
    aws_codepipeline as codepipeline,
    aws_sns_subscriptions as subs,
    CfnOutput
)
from constructs import Construct
from constants import Github, Project, Account, Email
from infrastructure.infrastructure import InfrastructureStack


class DeployStage(Stage):
    def __init__(self, scope: Construct, id: str, env: Environment, environment: str, **kwargs) -> None:
        super().__init__(scope, id, env=env, **kwargs)
        InfrastructureStack(self, f"InfrastructureStack-{environment}", env=env, environment=environment)


class CDKCodepipelineStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, environment: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        env = environment

        sending_mail_toppic = sns.Topic(self, "PipelineSendingEmailTopic", enforce_ssl=True)
        sending_mail_toppic.add_subscription(subs.EmailSubscription(Email.email))

        trigger_lambda_topic = sns.Topic(self, "TriggerLambdaTopic", enforce_ssl=True)

        git_input = pipelines.CodePipelineSource.connection(
            repo_string=f"{Github.OWNER}/{Github.REPO}",
            branch=env,
            connection_arn=Github.CONNECTION_ARN
        )

        removal_policy = RemovalPolicy.RETAIN if env=="prod" else RemovalPolicy.DESTROY
        auto_delete_objects = False if env == "prod" else True

        # Define an access logs bucket
        access_logs_bucket = s3.Bucket(self, "CDK-AccessLogsBucket",
            bucket_name=f"{Github.OWNER}-cdkpipeline-serveraccess-log-{env}",
            enforce_ssl=True,
            removal_policy=removal_policy,
            auto_delete_objects=auto_delete_objects)

        artifacts_bucket = s3.Bucket(self, "CDK-ArtifactsBucket",
            server_access_logs_bucket=access_logs_bucket,
            auto_delete_objects=auto_delete_objects,
            removal_policy=removal_policy,
            bucket_name=f"{Github.OWNER}-cdkpipeline-log-{env}", enforce_ssl=True)

        code_pipeline = codepipeline.Pipeline( self, "Pipeline",
            pipeline_name=f"{Project.PROJECT_NAME}-CDK-{env}-pipeline",
            cross_account_keys=False, artifact_bucket=artifacts_bucket)

        code_pipeline.notify_on(
            "FailedPipelineNotifications",
            sending_mail_toppic,
            events=[
                codepipeline.PipelineNotificationEvents.PIPELINE_EXECUTION_FAILED
            ]
        )

        code_pipeline.notify_on(
            "SucceededPipelineNotifications",
            trigger_lambda_topic,
            events=[
                codepipeline.PipelineNotificationEvents.PIPELINE_EXECUTION_SUCCEEDED
            ]
        )
        
        synth_step = pipelines.ShellStep(id="Synth",
            install_commands=[
                'pip install -r requirements.txt'
            ],
            commands=[
                'npx cdk synth'
            ],
            input=git_input)

        pipeline = pipelines.CodePipeline(self, 'CodePipeline', self_mutation=True,
            code_pipeline=code_pipeline, synth=synth_step)

        deployment_wave = pipeline.add_wave("DeploymentWave")

        deployment_wave.add_stage(DeployStage(self, f"DeployStage-{env}",
            env=Environment(account=Account.ACCOUNT_ID, region=Account.REGION), environment=env))

        if env != "dev":
            deployment_wave.add_pre(pipelines.ManualApprovalStep(f"Deploy-to-{env}-env"))

        CfnOutput(self, "ExportTriggerLambdaTopic", value=trigger_lambda_topic.topic_arn,
            export_name=f"Trigger-Lambda-topic-arn-{env}")
        CfnOutput(self, "SendingMailTopic", value=sending_mail_toppic.topic_arn,
            export_name=f"SNS-mailsending-arn-{env}")