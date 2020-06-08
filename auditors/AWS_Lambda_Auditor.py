import boto3
import datetime
import os
from dateutil import parser

lambdaClient = boto3.client("lambda")
cloudwatch = boto3.client("cloudwatch")
securityhub = boto3.client("securityhub")
sts = boto3.client("sts")

response = lambdaClient.list_functions()
functions = response["Functions"]

# create env vars
awsAccountId = sts.get_caller_identity()["Account"]
awsRegion = os.environ["AWS_REGION"]


def function_unused_check():
    for function in functions:
        functionName = str(function["FunctionName"])
        lambdaArn = str(function["FunctionArn"])
        metricResponse = cloudwatch.get_metric_data(
            MetricDataQueries=[
                {
                    "Id": "m1",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/Lambda",
                            "MetricName": "Invocations",
                            "Dimensions": [
                                {"Name": "FunctionName", "Value": functionName},
                            ],
                        },
                        "Period": 300,
                        "Stat": "Sum",
                    },
                }
            ],
            StartTime=datetime.datetime.now() - datetime.timedelta(days=30),
            EndTime=datetime.datetime.now(),
        )
        metrics = metricResponse["MetricDataResults"]
        for metric in metrics:
            insertionDate = parser.parse(function["LastModified"])
            differentiation = (
                datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
                - insertionDate
            )
            if len(metric["Values"]) > 0 or differentiation.days < 30:
                try:
                    iso8601Time = (
                        datetime.datetime.utcnow()
                        .replace(tzinfo=datetime.timezone.utc)
                        .isoformat()
                    )
                    response = securityhub.batch_import_findings(
                        Findings=[
                            {
                                "SchemaVersion": "2018-10-08",
                                "Id": lambdaArn + "/lambda-function-unused-check",
                                "ProductArn": "arn:aws:securityhub:"
                                + awsRegion
                                + ":"
                                + awsAccountId
                                + ":product/"
                                + awsAccountId
                                + "/default",
                                "GeneratorId": lambdaArn,
                                "AwsAccountId": awsAccountId,
                                "Types": [
                                    "Software and Configuration Checks/AWS Security Best Practices"
                                ],
                                "FirstObservedAt": iso8601Time,
                                "CreatedAt": iso8601Time,
                                "UpdatedAt": iso8601Time,
                                "Severity": {"Label": "INFORMATIONAL"},
                                "Confidence": 99,
                                "Title": "[Lambda.1] Lambda functions should be deleted after 30 days of no use",
                                "Description": "Lambda function "
                                + functionName
                                + " has been used or updated in the last 30 days.",
                                "Remediation": {
                                    "Recommendation": {
                                        "Text": "For more information on best practices for lambda functions refer to the Best Practices for Working with AWS Lambda Functions section of the Amazon Lambda Developer Guide",
                                        "Url": "https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html#function-configuration",
                                    }
                                },
                                "ProductFields": {"Product Name": "ElectricEye"},
                                "Resources": [
                                    {
                                        "Type": "AwsLambda",
                                        "Id": lambdaArn,
                                        "Partition": "aws",
                                        "Region": awsRegion,
                                    }
                                ],
                                "Compliance": {"Status": "PASSED"},
                                "Workflow": {"Status": "RESOLVED"},
                                "RecordState": "ARCHIVED",
                            }
                        ]
                    )
                    print(response)
                except Exception as e:
                    print(e)
            else:
                try:
                    iso8601Time = (
                        datetime.datetime.utcnow()
                        .replace(tzinfo=datetime.timezone.utc)
                        .isoformat()
                    )
                    response = securityhub.batch_import_findings(
                        Findings=[
                            {
                                "SchemaVersion": "2018-10-08",
                                "Id": lambdaArn + "/lambda-function-unused-check",
                                "ProductArn": "arn:aws:securityhub:"
                                + awsRegion
                                + ":"
                                + awsAccountId
                                + ":product/"
                                + awsAccountId
                                + "/default",
                                "GeneratorId": lambdaArn,
                                "AwsAccountId": awsAccountId,
                                "Types": [
                                    "Software and Configuration Checks/AWS Security Best Practices"
                                ],
                                "FirstObservedAt": iso8601Time,
                                "CreatedAt": iso8601Time,
                                "UpdatedAt": iso8601Time,
                                "Severity": {"Label": "LOW"},
                                "Confidence": 99,
                                "Title": "[Lambda.1] Lambda functions should be deleted after 30 days of no use",
                                "Description": "Lambda function "
                                + functionName
                                + " has not been used or updated in the last 30 days.",
                                "Remediation": {
                                    "Recommendation": {
                                        "Text": "For more information on best practices for lambda functions refer to the Best Practices for Working with AWS Lambda Functions section of the Amazon Lambda Developer Guide",
                                        "Url": "https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html#function-configuration",
                                    }
                                },
                                "ProductFields": {"Product Name": "ElectricEye"},
                                "Resources": [
                                    {
                                        "Type": "AwsLambda",
                                        "Id": lambdaArn,
                                        "Partition": "aws",
                                        "Region": awsRegion,
                                    }
                                ],
                                "Compliance": {"Status": "FAILED"},
                                "Workflow": {"Status": "NEW"},
                                "RecordState": "ACTIVE",
                            }
                        ]
                    )
                    print(response)
                except Exception as e:
                    print(e)


function_unused_check()