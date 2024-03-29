#This file is part of ElectricEye.
#SPDX-License-Identifier: Apache-2.0

#Licensed to the Apache Software Foundation (ASF) under one
#or more contributor license agreements.  See the NOTICE file
#distributed with this work for additional information
#regarding copyright ownership.  The ASF licenses this file
#to you under the Apache License, Version 2.0 (the
#"License"); you may not use this file except in compliance
#with the License.  You may obtain a copy of the License at

#http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing,
#software distributed under the License is distributed on an
#"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#KIND, either express or implied.  See the License for the
#specific language governing permissions and limitations
#under the License.

import datetime
from dateutil import parser
import boto3
import json
import botocore
from check_register import CheckRegister

registry = CheckRegister()

# boto3 clients
lambdas = boto3.client("lambda")
cloudwatch = boto3.client("cloudwatch")
ec2 = boto3.client("ec2")

def get_lambda_functions(cache):
    lambdaFunctions = []
    response = cache.get("get_lambda_functions")
    if response:
        return response
    paginator = lambdas.get_paginator('list_functions')
    if paginator:
        for page in paginator.paginate():
            for function in page["Functions"]:
                lambdaFunctions.append(function)
        cache["get_lambda_functions"] = lambdaFunctions
        return cache["get_lambda_functions"]

def get_lambda_layers(cache):
    lambdaLayers = []
    response = cache.get("get_lambda_layers")
    if response:
        return response
    paginator = lambdas.get_paginator('list_layers')
    if paginator:
        for page in paginator.paginate():
            for layer in page["Layers"]:
                lambdaLayers.append(layer)
        cache["get_lambda_layers"] = lambdaLayers
        return cache["get_lambda_layers"]

@registry.register_check("lambda")
def unused_function_check(cache: dict, awsAccountId: str, awsRegion: str, awsPartition: str) -> dict:
    """[Lambda.1] Lambda functions should be deleted after 30 days of no use"""
    # ISO Time
    iso8601Time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for function in get_lambda_functions(cache):
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
                            "Dimensions": [{"Name": "FunctionName", "Value": functionName},],
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
            modify_date = parser.parse(function["LastModified"])
            date_delta = datetime.datetime.now(datetime.timezone.utc) - modify_date
            if len(metric["Values"]) > 0 or date_delta.days < 30:
                # this is a passing check
                finding = {
                    "SchemaVersion": "2018-10-08",
                    "Id": f"{lambdaArn}/lambda-function-unused-check",
                    "ProductArn": f"arn:{awsPartition}:securityhub:{awsRegion}:{awsAccountId}:product/{awsAccountId}/default",
                    "GeneratorId": lambdaArn,
                    "AwsAccountId": awsAccountId,
                    "Types": ["Software and Configuration Checks/AWS Security Best Practices"],
                    "FirstObservedAt": iso8601Time,
                    "CreatedAt": iso8601Time,
                    "UpdatedAt": iso8601Time,
                    "Severity": {"Label": "INFORMATIONAL"},
                    "Confidence": 99,
                    "Title": "[Lambda.1] Lambda functions should be deleted after 30 days of no use",
                    "Description": f"Lambda function {functionName} has seen activity within the last 30 days.",
                    "Remediation": {
                        "Recommendation": {
                            "Text": "For more information on best practices for lambda functions refer to the Best Practices for Working with AWS Lambda Functions section of the Amazon Lambda Developer Guide",
                            "Url": "https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html#function-configuration",
                        }
                    },
                    "ProductFields": {"Product Name": "ElectricEye"},
                    "Resources": [
                        {
                            "Type": "AwsLambdaFunction",
                            "Id": lambdaArn,
                            "Partition": awsPartition,
                            "Region": awsRegion,
                            "Details": {
                                "AwsLambdaFunction": {
                                    "FunctionName": functionName
                                }
                            }
                        }
                    ],
                    "Compliance": {
                        "Status": "PASSED",
                        "RelatedRequirements": [
                            "NIST CSF ID.AM-2",
                            "NIST SP 800-53 CM-8",
                            "NIST SP 800-53 PM-5",
                            "AICPA TSC CC3.2",
                            "AICPA TSC CC6.1",
                            "ISO 27001:2013 A.8.1.1",
                            "ISO 27001:2013 A.8.1.2",
                            "ISO 27001:2013 A.12.5.1"
                        ]
                    },
                    "Workflow": {"Status": "RESOLVED"},
                    "RecordState": "ARCHIVED"
                }
                yield finding
            else:
                finding = {
                    "SchemaVersion": "2018-10-08",
                    "Id": f"{lambdaArn}/lambda-function-unused-check",
                    "ProductArn": f"arn:{awsPartition}:securityhub:{awsRegion}:{awsAccountId}:product/{awsAccountId}/default",
                    "GeneratorId": lambdaArn,
                    "AwsAccountId": awsAccountId,
                    "Types": ["Software and Configuration Checks/AWS Security Best Practices"],
                    "FirstObservedAt": iso8601Time,
                    "CreatedAt": iso8601Time,
                    "UpdatedAt": iso8601Time,
                    "Severity": {"Label": "LOW"},
                    "Confidence": 99,
                    "Title": "[Lambda.1] Lambda functions should be deleted after 30 days of no use",
                    "Description": f"Lambda function {functionName} has not been used within the last 30 days. Functions should be deleted if they are not used to avoid any potential malicious modifications and to lessen the consumption of default Lambda quotas such as stored code and number of functions.",
                    "Remediation": {
                        "Recommendation": {
                            "Text": "For more information on best practices for lambda functions refer to the Best Practices for Working with AWS Lambda Functions section of the Amazon Lambda Developer Guide",
                            "Url": "https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html#function-configuration",
                        }
                    },
                    "ProductFields": {"Product Name": "ElectricEye"},
                    "Resources": [
                        {
                            "Type": "AwsLambdaFunction",
                            "Id": lambdaArn,
                            "Partition": awsPartition,
                            "Region": awsRegion,
                            "Details": {
                                "AwsLambdaFunction": {
                                    "FunctionName": functionName
                                }
                            }
                        }
                    ],
                    "Compliance": {
                        "Status": "FAILED",
                        "RelatedRequirements": [
                            "NIST CSF ID.AM-2",
                            "NIST SP 800-53 CM-8",
                            "NIST SP 800-53 PM-5",
                            "AICPA TSC CC3.2",
                            "AICPA TSC CC6.1",
                            "ISO 27001:2013 A.8.1.1",
                            "ISO 27001:2013 A.8.1.2",
                            "ISO 27001:2013 A.12.5.1"
                        ]
                    },
                    "Workflow": {"Status": "NEW"},
                    "RecordState": "ACTIVE"
                }
                yield finding

@registry.register_check("lambda")
def function_tracing_check(cache: dict, awsAccountId: str, awsRegion: str, awsPartition: str) -> dict:
    """[Lambda.2] Lambda functions should use active tracing with AWS X-Ray"""
    # ISO Time
    iso8601Time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for function in get_lambda_functions(cache):
        functionName = str(function["FunctionName"])
        lambdaArn = str(function["FunctionArn"])
        # This is a passing check
        if str(function["TracingConfig"]["Mode"]) == "Active":
            finding = {
                "SchemaVersion": "2018-10-08",
                "Id": lambdaArn + "/lambda-active-tracing-check",
                "ProductArn": f"arn:{awsPartition}:securityhub:{awsRegion}:{awsAccountId}:product/{awsAccountId}/default",
                "GeneratorId": lambdaArn,
                "AwsAccountId": awsAccountId,
                "Types": ["Software and Configuration Checks/AWS Security Best Practices"],
                "FirstObservedAt": iso8601Time,
                "CreatedAt": iso8601Time,
                "UpdatedAt": iso8601Time,
                "Severity": {"Label": "INFORMATIONAL"},
                "Confidence": 99,
                "Title": "[Lambda.2] Lambda functions should use active tracing with AWS X-Ray",
                "Description": "Lambda function "
                + functionName
                + " has Active Tracing enabled.",
                "Remediation": {
                    "Recommendation": {
                        "Text": "To configure your Lambda functions send trace data to X-Ray refer to the Using AWS Lambda with AWS X-Ray section of the Amazon Lambda Developer Guide",
                        "Url": "https://docs.aws.amazon.com/lambda/latest/dg/services-xray.html"
                    }
                },
                "ProductFields": {"Product Name": "ElectricEye"},
                "Resources": [
                    {
                        "Type": "AwsLambdaFunction",
                        "Id": lambdaArn,
                        "Partition": awsPartition,
                        "Region": awsRegion,
                        "Details": {
                            "AwsLambdaFunction": {
                                "FunctionName": functionName,
                                "TracingConfig": {
                                    "Mode": str(function["TracingConfig"]["Mode"])
                                }
                            }
                        }
                    }
                ],
                "Compliance": {
                    "Status": "PASSED",
                    "RelatedRequirements": [
                        "NIST CSF DE.AE-3",
                        "NIST SP 800-53 AU-6",
                        "NIST SP 800-53 CA-7",
                        "NIST SP 800-53 IR-4",
                        "NIST SP 800-53 IR-5",
                        "NIST SP 800-53 IR-8",
                        "NIST SP 800-53 SI-4",
                        "AICPA TSC CC7.2",
                        "ISO 27001:2013 A.12.4.1",
                        "ISO 27001:2013 A.16.1.7",
                    ],
                },
                "Workflow": {"Status": "RESOLVED"},
                "RecordState": "ARCHIVED",
            }
            yield finding
        else:
            finding = {
                "SchemaVersion": "2018-10-08",
                "Id": lambdaArn + "/lambda-active-tracing-check",
                "ProductArn": f"arn:{awsPartition}:securityhub:{awsRegion}:{awsAccountId}:product/{awsAccountId}/default",
                "GeneratorId": lambdaArn,
                "AwsAccountId": awsAccountId,
                "Types": ["Software and Configuration Checks/AWS Security Best Practices"],
                "FirstObservedAt": iso8601Time,
                "CreatedAt": iso8601Time,
                "UpdatedAt": iso8601Time,
                "Severity": {"Label": "LOW"},
                "Confidence": 99,
                "Title": "[Lambda.2] Lambda functions should use active tracing with AWS X-Ray",
                "Description": "Lambda function "
                + functionName
                + " does not have Active Tracing enabled. Because X-Ray gives you an end-to-end view of an entire request, you can analyze latencies in your Functions and their backend services. You can use an X-Ray service map to view the latency of an entire request and that of the downstream services that are integrated with X-Ray. Refer to the remediation instructions if this configuration is not intended.",
                "Remediation": {
                    "Recommendation": {
                        "Text": "To configure your Lambda functions send trace data to X-Ray refer to the Using AWS Lambda with AWS X-Ray section of the Amazon Lambda Developer Guide",
                        "Url": "https://docs.aws.amazon.com/lambda/latest/dg/services-xray.html"
                    }
                },
                "ProductFields": {"Product Name": "ElectricEye"},
                "Resources": [
                    {
                        "Type": "AwsLambdaFunction",
                        "Id": lambdaArn,
                        "Partition": awsPartition,
                        "Region": awsRegion,
                        "Details": {
                            "AwsLambdaFunction": {
                                "FunctionName": functionName,
                                "TracingConfig": {
                                    "Mode": str(function["TracingConfig"]["Mode"])
                                }
                            }
                        }
                    }
                ],
                "Compliance": {
                    "Status": "FAILED",
                    "RelatedRequirements": [
                        "NIST CSF DE.AE-3",
                        "NIST SP 800-53 AU-6",
                        "NIST SP 800-53 CA-7",
                        "NIST SP 800-53 IR-4",
                        "NIST SP 800-53 IR-5",
                        "NIST SP 800-53 IR-8",
                        "NIST SP 800-53 SI-4",
                        "AICPA TSC CC7.2",
                        "ISO 27001:2013 A.12.4.1",
                        "ISO 27001:2013 A.16.1.7",
                    ],
                },
                "Workflow": {"Status": "NEW"},
                "RecordState": "ACTIVE"
            }
            yield finding

@registry.register_check("lambda")
def function_code_signer_check(cache: dict, awsAccountId: str, awsRegion: str, awsPartition: str) -> dict:
    """[Lambda.3] Lambda functions should use code signing from AWS Signer to ensure trusted code runs in a Function"""
    # ISO Time
    iso8601Time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for function in get_lambda_functions(cache):
        functionName = str(function["FunctionName"])
        lambdaArn = str(function["FunctionArn"])
        # This is a passing check
        try:
            signingJobArn = str(function["SigningJobArn"])
            finding = {
                "SchemaVersion": "2018-10-08",
                "Id": f"{lambdaArn}/lambda-code-signing-check",
                "ProductArn": f"arn:{awsPartition}:securityhub:{awsRegion}:{awsAccountId}:product/{awsAccountId}/default",
                "GeneratorId": lambdaArn,
                "AwsAccountId": awsAccountId,
                "Types": ["Software and Configuration Checks/AWS Security Best Practices"],
                "FirstObservedAt": iso8601Time,
                "CreatedAt": iso8601Time,
                "UpdatedAt": iso8601Time,
                "Severity": {"Label": "INFORMATIONAL"},
                "Confidence": 99,
                "Title": "[Lambda.3] Lambda functions should use code signing from AWS Signer to ensure trusted code runs in a Function",
                "Description": f"Lambda function {functionName} has an AWS code signing job configured at {signingJobArn}.",
                "Remediation": {
                    "Recommendation": {
                        "Text": "To configure code signing for your Functions refer to the Configuring code signing for AWS Lambda section of the Amazon Lambda Developer Guide",
                        "Url": "https://docs.aws.amazon.com/lambda/latest/dg/configuration-codesigning.html"
                    }
                },
                "ProductFields": {"Product Name": "ElectricEye"},
                "Resources": [
                    {
                        "Type": "AwsLambdaFunction",
                        "Id": lambdaArn,
                        "Partition": awsPartition,
                        "Region": awsRegion,
                        "Details": {
                            "AwsLambdaFunction": {
                                "FunctionName": functionName
                            }
                        }
                    }
                ],
                "Compliance": {
                    "Status": "PASSED",
                    "RelatedRequirements": [
                        "NIST CSF ID.SC-2",
                        "NIST SP 800-53 RA-2",
                        "NIST SP 800-53 RA-3",
                        "NIST SP 800-53 PM-9",
                        "NIST SP 800-53 SA-12",
                        "NIST SP 800-53 SA-14",
                        "NIST SP 800-53 SA-15",
                        "AICPA TSC CC7.2",
                        "ISO 27001:2013 A.15.2.1",
                        "ISO 27001:2013 A.15.2.2",
                    ],
                },
                "Workflow": {"Status": "RESOLVED"},
                "RecordState": "ARCHIVED",
            }
            yield finding
        except KeyError:
            finding = {
                "SchemaVersion": "2018-10-08",
                "Id": f"{lambdaArn}/lambda-code-signing-check",
                "ProductArn": f"arn:{awsPartition}:securityhub:{awsRegion}:{awsAccountId}:product/{awsAccountId}/default",
                "GeneratorId": lambdaArn,
                "AwsAccountId": awsAccountId,
                "Types": ["Software and Configuration Checks/AWS Security Best Practices"],
                "FirstObservedAt": iso8601Time,
                "CreatedAt": iso8601Time,
                "UpdatedAt": iso8601Time,
                "Severity": {"Label": "MEDIUM"},
                "Confidence": 99,
                "Title": "[Lambda.3] Lambda functions should use code signing from AWS Signer to ensure trusted code runs in a Function",
                "Description": f"Lambda function {functionName} does not have an AWS code signing job configured. Code signing for AWS Lambda helps to ensure that only trusted code runs in your Lambda functions. When you enable code signing for a function, Lambda checks every code deployment and verifies that the code package is signed by a trusted source. Refer to the remediation instructions if this configuration is not intended.",
                "Remediation": {
                    "Recommendation": {
                        "Text": "To configure code signing for your Functions refer to the Configuring code signing for AWS Lambda section of the Amazon Lambda Developer Guide",
                        "Url": "https://docs.aws.amazon.com/lambda/latest/dg/configuration-codesigning.html"
                    }
                },
                "ProductFields": {"Product Name": "ElectricEye"},
                "Resources": [
                    {
                        "Type": "AwsLambdaFunction",
                        "Id": lambdaArn,
                        "Partition": awsPartition,
                        "Region": awsRegion,
                        "Details": {
                            "AwsLambdaFunction": {
                                "FunctionName": functionName
                            }
                        }
                    }
                ],
                "Compliance": {
                    "Status": "FAILED",
                    "RelatedRequirements": [
                        "NIST CSF ID.SC-2",
                        "NIST SP 800-53 RA-2",
                        "NIST SP 800-53 RA-3",
                        "NIST SP 800-53 PM-9",
                        "NIST SP 800-53 SA-12",
                        "NIST SP 800-53 SA-14",
                        "NIST SP 800-53 SA-15",
                        "AICPA TSC CC7.2",
                        "ISO 27001:2013 A.15.2.1",
                        "ISO 27001:2013 A.15.2.2"
                    ]
                },
                "Workflow": {"Status": "NEW"},
                "RecordState": "ACTIVE"
            }
            yield finding

@registry.register_check("lambda")
def public_lambda_layer_check(cache: dict, awsAccountId: str, awsRegion: str, awsPartition: str) -> dict:
    """[Lambda.4] Lambda layers should not be publicly shared"""
    # ISO Time
    iso8601Time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for layer in get_lambda_layers(cache):
        layerName = str(layer["LayerName"])
        layerArn = str(layer["LatestMatchingVersion"]["LayerVersionArn"])
        try:
            compatibleRuntimes = layer["LatestMatchingVersion"]["CompatibleRuntimes"]
        except KeyError:
            compatibleRuntimes = []
        createDate = parser.parse(layer["LatestMatchingVersion"]["CreatedDate"]).isoformat()
        layerVersion = layer["LatestMatchingVersion"]["Version"]
        # Get the layer Policy
        layerPolicy = json.loads(lambdas.get_layer_version_policy(
            LayerName=layerName,
            VersionNumber=layerVersion
        )["Policy"])
        # Evaluate layer Policy
        for s in layerPolicy["Statement"]:
            principal = s["Principal"]
            effect = s["Effect"]
            try:
                conditionalPolicy = s["Condition"]["StringEquals"]["aws:PrincipalOrgID"]
                hasCondition = True
                del conditionalPolicy
            except KeyError:
                hasCondition = False
            # this evaluation logic is a failing check
            if (principal == "*" and effect == "Allow" and hasCondition == False):
                # this is a failing check
                finding = {
                    "SchemaVersion": "2018-10-08",
                    "Id": f"{layerArn}/public-lambda-layer-check",
                    "ProductArn": f"arn:{awsPartition}:securityhub:{awsRegion}:{awsAccountId}:product/{awsAccountId}/default",
                    "GeneratorId": layerArn,
                    "AwsAccountId": awsAccountId,
                    "Types": [
                        "Software and Configuration Checks/AWS Security Best Practices",
                        "Effects/Data Exposure",
                    ],
                    "FirstObservedAt": iso8601Time,
                    "CreatedAt": iso8601Time,
                    "UpdatedAt": iso8601Time,
                    "Severity": {"Label": "HIGH"},
                    "Confidence": 99,
                    "Title": "[Lambda.4] Lambda layers should not be publicly shared",
                    "Description": f"Lambda layer {layerName} is publicly shared without specifying a conditional access policy. Inadvertently sharing Lambda layers can potentially expose business logic or sensitive details within the Layer depending on how it is configured and thus all Layer sharing should be carefully reviewed. Refer to the remediation instructions if this configuration is not intended.",
                    "Remediation": {
                        "Recommendation": {
                            "Text": "For more information on sharing Lambda Layers and modifiying their permissions refer to the Configuring layer permissions section of the Amazon Lambda Developer Guide",
                            "Url": "https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html#configuration-layers-permissions"
                        }
                    },
                    "ProductFields": {"Product Name": "ElectricEye"},
                    "Resources": [
                        {
                            "Type": "AwsLambdaLayerVersion",
                            "Id": layerArn,
                            "Partition": awsPartition,
                            "Region": awsRegion,
                            "Details": {
                                "AwsLambdaLayerVersion": {
                                    "Version": layerVersion,
                                    "CompatibleRuntimes": compatibleRuntimes,
                                    "CreatedDate": createDate
                                }
                            }
                        }
                    ],
                    "Compliance": {
                        "Status": "FAILED",
                        "RelatedRequirements": [
                            "NIST CSF PR.AC-3",
                            "NIST SP 800-53 AC-1",
                            "NIST SP 800-53 AC-17",
                            "NIST SP 800-53 AC-19",
                            "NIST SP 800-53 AC-20",
                            "NIST SP 800-53 SC-15",
                            "AICPA TSC CC6.6",
                            "ISO 27001:2013 A.6.2.1",
                            "ISO 27001:2013 A.6.2.2",
                            "ISO 27001:2013 A.11.2.6",
                            "ISO 27001:2013 A.13.1.1",
                            "ISO 27001:2013 A.13.2.1"
                        ]
                    },
                    "Workflow": {"Status": "NEW"},
                    "RecordState": "ACTIVE"
                }
                yield finding
            else:
                finding = {
                    "SchemaVersion": "2018-10-08",
                    "Id": f"{layerArn}/public-lambda-layer-check",
                    "ProductArn": f"arn:{awsPartition}:securityhub:{awsRegion}:{awsAccountId}:product/{awsAccountId}/default",
                    "GeneratorId": layerArn,
                    "AwsAccountId": awsAccountId,
                    "Types": [
                        "Software and Configuration Checks/AWS Security Best Practices",
                        "Effects/Data Exposure",
                    ],
                    "FirstObservedAt": iso8601Time,
                    "CreatedAt": iso8601Time,
                    "UpdatedAt": iso8601Time,
                    "Severity": {"Label": "INFORMATIONAL"},
                    "Confidence": 99,
                    "Title": "[Lambda.4] Lambda layers should not be publicly shared",
                    "Description": f"Lambda layer {layerName} is not publicly shared.",
                    "Remediation": {
                        "Recommendation": {
                            "Text": "For more information on sharing Lambda Layers and modifiying their permissions refer to the Configuring layer permissions section of the Amazon Lambda Developer Guide",
                            "Url": "https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html#configuration-layers-permissions"
                        }
                    },
                    "ProductFields": {"Product Name": "ElectricEye"},
                    "Resources": [
                        {
                            "Type": "AwsLambdaLayerVersion",
                            "Id": layerArn,
                            "Partition": awsPartition,
                            "Region": awsRegion,
                            "Details": {
                                "AwsLambdaLayerVersion": {
                                    "Version": layerVersion,
                                    "CompatibleRuntimes": compatibleRuntimes,
                                    "CreatedDate": createDate
                                }
                            }
                        }
                    ],
                    "Compliance": {
                        "Status": "PASSED",
                        "RelatedRequirements": [
                            "NIST CSF PR.AC-3",
                            "NIST SP 800-53 AC-1",
                            "NIST SP 800-53 AC-17",
                            "NIST SP 800-53 AC-19",
                            "NIST SP 800-53 AC-20",
                            "NIST SP 800-53 SC-15",
                            "AICPA TSC CC6.6",
                            "ISO 27001:2013 A.6.2.1",
                            "ISO 27001:2013 A.6.2.2",
                            "ISO 27001:2013 A.11.2.6",
                            "ISO 27001:2013 A.13.1.1",
                            "ISO 27001:2013 A.13.2.1"
                        ]
                    },
                    "Workflow": {"Status": "RESOLVED"},
                    "RecordState": "ARCHIVED"
                }
                yield finding

@registry.register_check("lambda")
def public_lambda_function_check(cache: dict, awsAccountId: str, awsRegion: str, awsPartition: str) -> dict:
    """[Lambda.5] Lambda functions should not be publicly shared"""
    # ISO Time
    iso8601Time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for function in get_lambda_functions(cache):
        functionName = str(function["FunctionName"])
        lambdaArn = str(function["FunctionArn"])
        # Get function policy
        try:
            funcPolicy = json.loads(lambdas.get_policy(FunctionName=functionName)["Policy"])
            # Evaluate layer Policy
            for s in funcPolicy["Statement"]:
                principal = s["Principal"]
                effect = s["Effect"]
                try:
                    # check for any condition which can be "aws:PrincipalOrgId" or "aws:SourceAccount" or "aws:SourceArn"
                    conditionalPolicy = s["Condition"]
                    hasCondition = True
                    del conditionalPolicy
                except KeyError:
                    hasCondition = False
                # this evaluation logic is a failing check
                if (principal == "*" and effect == "Allow" and hasCondition == False):
                    # this is a failing check
                    finding = {
                        "SchemaVersion": "2018-10-08",
                        "Id": f"{lambdaArn}/public-lambda-function-check",
                        "ProductArn": f"arn:{awsPartition}:securityhub:{awsRegion}:{awsAccountId}:product/{awsAccountId}/default",
                        "GeneratorId": lambdaArn,
                        "AwsAccountId": awsAccountId,
                        "Types": [
                            "Software and Configuration Checks/AWS Security Best Practices",
                            "Effects/Data Exposure",
                        ],
                        "FirstObservedAt": iso8601Time,
                        "CreatedAt": iso8601Time,
                        "UpdatedAt": iso8601Time,
                        "Severity": {"Label": "MEDIUM"},
                        "Confidence": 99,
                        "Title": "[Lambda.5] Lambda functions should not be publicly shared",
                        "Description": f"Lambda function {functionName} is allowed to be publicly invoked. While public invocation still requires understanding the Lambda function's metadata and having valid AWS credentials, functions should never be allowed to be freely invoked and should instead have a calling service or an API Gateway. Refer to the remediation instructions if this configuration is not intended.",
                        "Remediation": {
                            "Recommendation": {
                                "Text": "For more information on Lambda function resource-based policies and modifiying their permissions refer to the Using resource-based policies for AWS Lambda section of the Amazon Lambda Developer Guide",
                                "Url": "https://docs.aws.amazon.com/lambda/latest/dg/access-control-resource-based.html"
                            }
                        },
                        "ProductFields": {"Product Name": "ElectricEye"},
                        "Resources": [
                            {
                                "Type": "AwsLambdaFunction",
                                "Id": lambdaArn,
                                "Partition": awsPartition,
                                "Region": awsRegion,
                                "Details": {
                                    "AwsLambdaFunction": {
                                        "FunctionName": functionName
                                    }
                                }
                            }
                        ],
                        "Compliance": {
                            "Status": "FAILED",
                            "RelatedRequirements": [
                                "NIST CSF PR.AC-3",
                                "NIST SP 800-53 AC-1",
                                "NIST SP 800-53 AC-17",
                                "NIST SP 800-53 AC-19",
                                "NIST SP 800-53 AC-20",
                                "NIST SP 800-53 SC-15",
                                "AICPA TSC CC6.6",
                                "ISO 27001:2013 A.6.2.1",
                                "ISO 27001:2013 A.6.2.2",
                                "ISO 27001:2013 A.11.2.6",
                                "ISO 27001:2013 A.13.1.1",
                                "ISO 27001:2013 A.13.2.1"
                            ]
                        },
                        "Workflow": {"Status": "NEW"},
                        "RecordState": "ACTIVE"
                    }
                    yield finding
                else:
                    # this is a passing check
                    finding = {
                        "SchemaVersion": "2018-10-08",
                        "Id": f"{lambdaArn}/public-lambda-function-check",
                        "ProductArn": f"arn:{awsPartition}:securityhub:{awsRegion}:{awsAccountId}:product/{awsAccountId}/default",
                        "GeneratorId": lambdaArn,
                        "AwsAccountId": awsAccountId,
                        "Types": [
                            "Software and Configuration Checks/AWS Security Best Practices",
                            "Effects/Data Exposure",
                        ],
                        "FirstObservedAt": iso8601Time,
                        "CreatedAt": iso8601Time,
                        "UpdatedAt": iso8601Time,
                        "Severity": {"Label": "INFORMATIONAL"},
                        "Confidence": 99,
                        "Title": "[Lambda.5] Lambda functions should not be publicly shared",
                        "Description": f"Lambda function {functionName} is not allowed to be publicly invoked.",
                        "Remediation": {
                            "Recommendation": {
                                "Text": "For more information on Lambda function resource-based policies and modifiying their permissions refer to the Using resource-based policies for AWS Lambda section of the Amazon Lambda Developer Guide",
                                "Url": "https://docs.aws.amazon.com/lambda/latest/dg/access-control-resource-based.html"
                            }
                        },
                        "ProductFields": {"Product Name": "ElectricEye"},
                        "Resources": [
                            {
                                "Type": "AwsLambdaFunction",
                                "Id": lambdaArn,
                                "Partition": awsPartition,
                                "Region": awsRegion,
                                "Details": {
                                    "AwsLambdaFunction": {
                                        "FunctionName": functionName
                                    }
                                }
                            }
                        ],
                        "Compliance": {
                            "Status": "PASSED",
                            "RelatedRequirements": [
                                "NIST CSF PR.AC-3",
                                "NIST SP 800-53 AC-1",
                                "NIST SP 800-53 AC-17",
                                "NIST SP 800-53 AC-19",
                                "NIST SP 800-53 AC-20",
                                "NIST SP 800-53 SC-15",
                                "AICPA TSC CC6.6",
                                "ISO 27001:2013 A.6.2.1",
                                "ISO 27001:2013 A.6.2.2",
                                "ISO 27001:2013 A.11.2.6",
                                "ISO 27001:2013 A.13.1.1",
                                "ISO 27001:2013 A.13.2.1"
                            ]
                        },
                        "Workflow": {"Status": "RESOLVED"},
                        "RecordState": "ARCHIVED"
                    }
                    yield finding
        except botocore.exceptions.ClientError as error:
            if error.response['Error']['Code'] == 'ResourceNotFoundException':
                # this is a passing check
                finding = {
                    "SchemaVersion": "2018-10-08",
                    "Id": f"{lambdaArn}/public-lambda-function-check",
                    "ProductArn": f"arn:{awsPartition}:securityhub:{awsRegion}:{awsAccountId}:product/{awsAccountId}/default",
                    "GeneratorId": lambdaArn,
                    "AwsAccountId": awsAccountId,
                    "Types": [
                        "Software and Configuration Checks/AWS Security Best Practices",
                        "Effects/Data Exposure",
                    ],
                    "FirstObservedAt": iso8601Time,
                    "CreatedAt": iso8601Time,
                    "UpdatedAt": iso8601Time,
                    "Severity": {"Label": "INFORMATIONAL"},
                    "Confidence": 99,
                    "Title": "[Lambda.5] Lambda functions should not be publicly shared",
                    "Description": f"Lambda function {functionName} is not allowed to be publicly invoked due to not having an invocation policy and is thus exempt from this check.",
                    "Remediation": {
                        "Recommendation": {
                            "Text": "For more information on Lambda function resource-based policies and modifiying their permissions refer to the Using resource-based policies for AWS Lambda section of the Amazon Lambda Developer Guide",
                            "Url": "https://docs.aws.amazon.com/lambda/latest/dg/access-control-resource-based.html"
                        }
                    },
                    "ProductFields": {"Product Name": "ElectricEye"},
                    "Resources": [
                        {
                            "Type": "AwsLambdaFunction",
                            "Id": lambdaArn,
                            "Partition": awsPartition,
                            "Region": awsRegion,
                            "Details": {
                                "AwsLambdaFunction": {
                                    "FunctionName": functionName
                                }
                            }
                        }
                    ],
                    "Compliance": {
                        "Status": "PASSED",
                        "RelatedRequirements": [
                            "NIST CSF PR.AC-3",
                            "NIST SP 800-53 AC-1",
                            "NIST SP 800-53 AC-17",
                            "NIST SP 800-53 AC-19",
                            "NIST SP 800-53 AC-20",
                            "NIST SP 800-53 SC-15",
                            "AICPA TSC CC6.6",
                            "ISO 27001:2013 A.6.2.1",
                            "ISO 27001:2013 A.6.2.2",
                            "ISO 27001:2013 A.11.2.6",
                            "ISO 27001:2013 A.13.1.1",
                            "ISO 27001:2013 A.13.2.1"
                        ]
                    },
                    "Workflow": {"Status": "RESOLVED"},
                    "RecordState": "ARCHIVED"
                }
                yield finding

@registry.register_check("lambda")
def lambda_supported_runtimes_check(cache: dict, awsAccountId: str, awsRegion: str, awsPartition: str) -> dict:
    """[Lambda.6] Lambda functions should use supported runtimes"""
    # Supported Runtimes
    supportedRuntimes = [
        'nodejs14.x',
        'nodejs12.x',
        'python3.9',
        'python3.8',
        'python3.7',
        'python3.6',
        'ruby2.7',
        'java11',
        'java8',
        'java8.al2',
        'go1.x',
        'dotnet6',
        'dotnetcore3.1',
        'provided.al2',
        'provided'
    ]
    # ISO Time
    iso8601Time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for function in get_lambda_functions(cache):
        functionName = str(function["FunctionName"])
        lambdaArn = str(function["FunctionArn"])
        lambdaRuntime = str(function["Runtime"])
        if lambdaRuntime not in supportedRuntimes:
            # this is a failing check
            finding = {
                "SchemaVersion": "2018-10-08",
                "Id": f"{lambdaArn}/lambda-supported-runtimes-check",
                "ProductArn": f"arn:{awsPartition}:securityhub:{awsRegion}:{awsAccountId}:product/{awsAccountId}/default",
                "GeneratorId": lambdaArn,
                "AwsAccountId": awsAccountId,
                "Types": ["Software and Configuration Checks/AWS Security Best Practices"],
                "FirstObservedAt": iso8601Time,
                "CreatedAt": iso8601Time,
                "UpdatedAt": iso8601Time,
                "Severity": {"Label": "MEDIUM"},
                "Confidence": 99,
                "Title": "[Lambda.6] Lambda functions should use supported runtimes",
                "Description": f"Lambda function {functionName} is not using a supported runtime version. Using support runtimes is Lambda runtimes are built around a combination of operating system, programming language, and software libraries that are subject to maintenance and security updates. When a runtime component is no longer supported for security updates, Lambda deprecates the runtime. Even though you cannot create functions that use the deprecated runtime, the function is still available to process invocation events. Make sure that your Lambda functions are current and do not use out-of-date runtime environments. Refer to the remediation instructions if this configuration is not intended.",
                "Remediation": {
                    "Recommendation": {
                        "Text": "For more information on the supported runtimes that this control checks for the supported languages refer to the AWS Lambda runtimes section of the Amazon Lambda Developer Guide",
                        "Url": "https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html"
                    }
                },
                "ProductFields": {"Product Name": "ElectricEye"},
                "Resources": [
                    {
                        "Type": "AwsLambdaFunction",
                        "Id": lambdaArn,
                        "Partition": awsPartition,
                        "Region": awsRegion,
                        "Details": {
                            "AwsLambdaFunction": {
                                "FunctionName": functionName
                            }
                        }
                    }
                ],
                "Compliance": {
                    "Status": "FAILED",
                    "RelatedRequirements": [
                        "NIST CSF PR.AC-3",
                        "NIST SP 800-53 AC-1",
                        "NIST SP 800-53 AC-17",
                        "NIST SP 800-53 AC-19",
                        "NIST SP 800-53 AC-20",
                        "NIST SP 800-53 SC-15",
                        "AICPA TSC CC6.6",
                        "ISO 27001:2013 A.6.2.1",
                        "ISO 27001:2013 A.6.2.2",
                        "ISO 27001:2013 A.11.2.6",
                        "ISO 27001:2013 A.13.1.1",
                        "ISO 27001:2013 A.13.2.1"
                    ]
                },
                "Workflow": {"Status": "NEW"},
                "RecordState": "ACTIVE"
            }
            yield finding
        else:
            # this is a passing check
            finding = {
                "SchemaVersion": "2018-10-08",
                "Id": f"{lambdaArn}/lambda-supported-runtimes-check",
                "ProductArn": f"arn:{awsPartition}:securityhub:{awsRegion}:{awsAccountId}:product/{awsAccountId}/default",
                "GeneratorId": lambdaArn,
                "AwsAccountId": awsAccountId,
                "Types": ["Software and Configuration Checks/AWS Security Best Practices"],
                "FirstObservedAt": iso8601Time,
                "CreatedAt": iso8601Time,
                "UpdatedAt": iso8601Time,
                "Severity": {"Label": "INFORMATIONAL"},
                "Confidence": 99,
                "Title": "[Lambda.6] Lambda functions should use supported runtimes",
                "Description": f"Lambda function {functionName} is using a supported runtime version.",
                "Remediation": {
                    "Recommendation": {
                        "Text": "For more information on the supported runtimes that this control checks for the supported languages refer to the AWS Lambda runtimes section of the Amazon Lambda Developer Guide",
                        "Url": "https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html"
                    }
                },
                "ProductFields": {"Product Name": "ElectricEye"},
                "Resources": [
                    {
                        "Type": "AwsLambdaFunction",
                        "Id": lambdaArn,
                        "Partition": awsPartition,
                        "Region": awsRegion,
                        "Details": {
                            "AwsLambdaFunction": {
                                "FunctionName": functionName
                            }
                        }
                    }
                ],
                "Compliance": {
                    "Status": "PASSED",
                    "RelatedRequirements": [
                        "NIST CSF PR.AC-3",
                        "NIST SP 800-53 AC-1",
                        "NIST SP 800-53 AC-17",
                        "NIST SP 800-53 AC-19",
                        "NIST SP 800-53 AC-20",
                        "NIST SP 800-53 SC-15",
                        "AICPA TSC CC6.6",
                        "ISO 27001:2013 A.6.2.1",
                        "ISO 27001:2013 A.6.2.2",
                        "ISO 27001:2013 A.11.2.6",
                        "ISO 27001:2013 A.13.1.1",
                        "ISO 27001:2013 A.13.2.1"
                    ]
                },
                "Workflow": {"Status": "RESOLVED"},
                "RecordState": "ARCHIVED"
            }
            yield finding

@registry.register_check("lambda")
def lambda_vpc_ha_subnets_check(cache: dict, awsAccountId: str, awsRegion: str, awsPartition: str) -> dict:
    """[Lambda.7] Lambda functions in VPCs should use more than one Availability Zone"""
    # Create empty list to hold unique Subnet IDs - for future lookup against AZs
    uSubnets = []
    # Create another empty list to hold unique AZs based on Subnets
    uAzs = []
    # ISO Time
    iso8601Time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for function in get_lambda_functions(cache):
        functionName = str(function["FunctionName"])
        lambdaArn = str(function["FunctionArn"])
        # check specific metadata
        try:
            # append unique Subnets to the "uSubnets" list
            for snet in function["VpcConfig"]["SubnetIds"]:
                if snet not in uSubnets:
                    uSubnets.append(snet)
                else:
                    continue
            # look up each Subnet for the Lambda function and determine the AZ-ID
            # write unique AZ-IDs into the "uAzs" list for final determination
            for subnet in ec2.describe_subnets(SubnetIds=uSubnets)["Subnets"]:
                azId = str(subnet["AvailabilityZone"])
                if azId not in uAzs:
                    uAzs.append(azId)
                else:
                    continue
            if len(uAzs) <= 1:
                # this is a failing check
                finding = {
                    "SchemaVersion": "2018-10-08",
                    "Id": f"{lambdaArn}/lambda-vpc-subnet-ha-check",
                    "ProductArn": f"arn:{awsPartition}:securityhub:{awsRegion}:{awsAccountId}:product/{awsAccountId}/default",
                    "GeneratorId": lambdaArn,
                    "AwsAccountId": awsAccountId,
                    "Types": ["Software and Configuration Checks/AWS Security Best Practices"],
                    "FirstObservedAt": iso8601Time,
                    "CreatedAt": iso8601Time,
                    "UpdatedAt": iso8601Time,
                    "Severity": {"Label": "MEDIUM"},
                    "Confidence": 99,
                    "Title": "[Lambda.7] Lambda functions in VPCs should use more than one Availability Zone",
                    "Description": f"Lambda function {functionName} is only deployed to a Single Availability Zone. Deploying resources across multiple Availability Zones is an AWS best practice to ensure high availability within your architecture. Availability is a core pillar in the confidentiality, integrity, and availability triad security model. All Lambda functions should have a multi-Availability Zone deployment to ensure that a single zone of failure does not cause a total disruption of operations. Refer to the remediation instructions if this configuration is not intended.",
                    "Remediation": {
                        "Recommendation": {
                            "Text": "For more information Lambda function networking and HA requirements refer to the VPC networking for Lambda section of the Amazon Lambda Developer Guide",
                            "Url": "https://docs.aws.amazon.com/lambda/latest/dg/foundation-networking.html"
                        }
                    },
                    "ProductFields": {"Product Name": "ElectricEye"},
                    "Resources": [
                        {
                            "Type": "AwsLambdaFunction",
                            "Id": lambdaArn,
                            "Partition": awsPartition,
                            "Region": awsRegion,
                            "Details": {
                                "AwsLambdaFunction": {
                                    "FunctionName": functionName
                                }
                            }
                        }
                    ],
                    "Compliance": {
                        "Status": "FAILED",
                        "RelatedRequirements": [
                            "NIST CSF ID.BE-5",
                            "NIST CSF PR.PT-5",
                            "NIST SP 800-53 CP-2",
                            "NIST SP 800-53 CP-11",
                            "NIST SP 800-53 SA-13",
                            "NIST SP 800-53 SA14",
                            "AICPA TSC CC3.1",
                            "AICPA TSC A1.2",
                            "ISO 27001:2013 A.11.1.4",
                            "ISO 27001:2013 A.17.1.1",
                            "ISO 27001:2013 A.17.1.2",
                            "ISO 27001:2013 A.17.2.1"
                        ]
                    },
                    "Workflow": {"Status": "NEW"},
                    "RecordState": "ACTIVE"
                }
                yield finding
            else:
                # this is a passing check
                finding = {
                    "SchemaVersion": "2018-10-08",
                    "Id": f"{lambdaArn}/lambda-vpc-subnet-ha-check",
                    "ProductArn": f"arn:{awsPartition}:securityhub:{awsRegion}:{awsAccountId}:product/{awsAccountId}/default",
                    "GeneratorId": lambdaArn,
                    "AwsAccountId": awsAccountId,
                    "Types": ["Software and Configuration Checks/AWS Security Best Practices"],
                    "FirstObservedAt": iso8601Time,
                    "CreatedAt": iso8601Time,
                    "UpdatedAt": iso8601Time,
                    "Severity": {"Label": "INFORMATIONAL"},
                    "Confidence": 99,
                    "Title": "[Lambda.7] Lambda functions in VPCs should use more than one Availability Zone",
                    "Description": f"Lambda function {functionName} is deployed to at least two Availability Zones.",
                    "Remediation": {
                        "Recommendation": {
                            "Text": "For more information Lambda function networking and HA requirements refer to the VPC networking for Lambda section of the Amazon Lambda Developer Guide",
                            "Url": "https://docs.aws.amazon.com/lambda/latest/dg/foundation-networking.html"
                        }
                    },
                    "ProductFields": {"Product Name": "ElectricEye"},
                    "Resources": [
                        {
                            "Type": "AwsLambdaFunction",
                            "Id": lambdaArn,
                            "Partition": awsPartition,
                            "Region": awsRegion,
                            "Details": {
                                "AwsLambdaFunction": {
                                    "FunctionName": functionName
                                }
                            }
                        }
                    ],
                    "Compliance": {
                        "Status": "PASSED",
                        "RelatedRequirements": [
                            "NIST CSF ID.BE-5",
                            "NIST CSF PR.PT-5",
                            "NIST SP 800-53 CP-2",
                            "NIST SP 800-53 CP-11",
                            "NIST SP 800-53 SA-13",
                            "NIST SP 800-53 SA14",
                            "AICPA TSC CC3.1",
                            "AICPA TSC A1.2",
                            "ISO 27001:2013 A.11.1.4",
                            "ISO 27001:2013 A.17.1.1",
                            "ISO 27001:2013 A.17.1.2",
                            "ISO 27001:2013 A.17.2.1"
                        ]
                    },
                    "Workflow": {"Status": "RESOLVED"},
                    "RecordState": "ARCHIVED"
                }
                yield finding
        except KeyError:
            # this is a passing check
            finding = {
                "SchemaVersion": "2018-10-08",
                "Id": f"{lambdaArn}/lambda-vpc-subnet-ha-check",
                "ProductArn": f"arn:{awsPartition}:securityhub:{awsRegion}:{awsAccountId}:product/{awsAccountId}/default",
                "GeneratorId": lambdaArn,
                "AwsAccountId": awsAccountId,
                "Types": ["Software and Configuration Checks/AWS Security Best Practices"],
                "FirstObservedAt": iso8601Time,
                "CreatedAt": iso8601Time,
                "UpdatedAt": iso8601Time,
                "Severity": {"Label": "INFORMATIONAL"},
                "Confidence": 99,
                "Title": "[Lambda.7] Lambda functions in VPCs should use more than one Availability Zone",
                "Description": f"Lambda function {functionName} is not deployed to a VPC and is thus exempt from this check.",
                "Remediation": {
                    "Recommendation": {
                        "Text": "For more information Lambda function networking and HA requirements refer to the VPC networking for Lambda section of the Amazon Lambda Developer Guide",
                        "Url": "https://docs.aws.amazon.com/lambda/latest/dg/foundation-networking.html"
                    }
                },
                "ProductFields": {"Product Name": "ElectricEye"},
                "Resources": [
                    {
                        "Type": "AwsLambdaFunction",
                        "Id": lambdaArn,
                        "Partition": awsPartition,
                        "Region": awsRegion,
                        "Details": {
                            "AwsLambdaFunction": {
                                "FunctionName": functionName
                            }
                        }
                    }
                ],
                "Compliance": {
                    "Status": "PASSED",
                    "RelatedRequirements": [
                        "NIST CSF ID.BE-5",
                        "NIST CSF PR.PT-5",
                        "NIST SP 800-53 CP-2",
                        "NIST SP 800-53 CP-11",
                        "NIST SP 800-53 SA-13",
                        "NIST SP 800-53 SA14",
                        "AICPA TSC CC3.1",
                        "AICPA TSC A1.2",
                        "ISO 27001:2013 A.11.1.4",
                        "ISO 27001:2013 A.17.1.1",
                        "ISO 27001:2013 A.17.1.2",
                        "ISO 27001:2013 A.17.2.1"
                    ]
                },
                "Workflow": {"Status": "RESOLVED"},
                "RecordState": "ARCHIVED"
            }
            yield finding