import aws_cdk as core
import aws_cdk.assertions as assertions

from infrastructure.sdk_python_devops_stack import SdkPythonDevopsStack

# example tests. To run these tests, uncomment this file along with the example
# resource in sdk_python_devops/sdk_python_devops_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = SdkPythonDevopsStack(app, "sdk-python-devops")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
