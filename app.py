#!/usr/bin/env python3
import aws_cdk as cdk
from cdk_pipeline.cdk_pipeline import CDKCodepipelineStack
from infrash_pipeline.infras_pipeline import InfrasPipelineStack
from constants import Account
from cdk_nag import AwsSolutionsChecks, NagSuppressions


app = cdk.App()
environment = app.node.try_get_context("env") or "dev"
valid_environments = ["dev", "test", "prod"]
if environment not in valid_environments:
    raise ValueError(f"Invalid environment '{environment}'. Must be one of {valid_environments}")

env=cdk.Environment(account=Account.ACCOUNT_ID, region=Account.REGION)

cdk_codepipeline_stack = CDKCodepipelineStack(app, f"CDKCodepipelineStack-{environment}",
    environment=environment, env=env)

suppressions = [
    {
        "id": "AwsSolutions-IAM5",
        "reason": "Wildcard permissions are necessary for the pipeline and deployment setup in this context."
    },
    {
        "id": "AwsSolutions-IAM4",
        "reason": "Using AWS managed CodeDeploy policy as it meets the necessary permissions requirements for this setup."
    },
    {
        "id": "AwsSolutions-CB4",
        "reason": "Could not find to way for CodeBuil encryption"
    }
]

NagSuppressions.add_stack_suppressions(cdk_codepipeline_stack, suppressions)

cdk.Aspects.of(app).add(AwsSolutionsChecks())

app.synth()
