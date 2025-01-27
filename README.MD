# Base64Loop CloudFormation Macro

The `Base64Loop` macro provides a template-wide `For::Each` loop on CloudFormation resources by processing in passed in Base64 parameter This gets around the issue of being unable to pass in JSON objects to CFN.

There are also additional keywords allowing you to get the Ref or Arn of all the Resources looped through, allowing policies to also be dynamically updated.


## How to install and use the Base64Loop macro in your AWS account



### Deploying

1. Deploy the macro stored in the base64loop-macro.yml, this contains the inline Lambda function.

```
aws cloudformation deploy \
    --stack-name base64loop-macro \
    --template-file base64loop-macro.yaml \
    --capabilities CAPABILITY_IAM
```

2. You can test on the command line using the below command. This will print the output template to the console.

```
python3 -u base64loop.py base64loop-test-s3.yml
```

3. To test out the macro's capabilities, try launching the provided example template:

```
aws cloudformation deploy \
    --stack-name base64loop-test \
    --template-file base64loop-test-s3.yml \
    --capabilities CAPABILITY_IAM
```



### Generating the Base64 Value

The Base64 data is an encoded Json Object list. The name of each object is the resource name that will be used in the cloudformation template, with the contents of the object key/values pairs being used to pass to each resource being made.

```
{
    "databucket": {
        "name": "zzzht1-databucket"
    },
    "metabucket": {
        "name": "zzzht1-metabucket"
    }
}
```

Once you have your data in this format. You will need to encode it using a Base64 encoder. It must be in proper JSON format and not just a string, so use a JSON loader like jq to process the file before encoding it.

Example:

Bash
```
ResourceListBase64=$(cat base64-json-example.json | jq -c '.' | base64 -w0)
```



### Looping Usage

To make use of the macro, add `Transform: Base64loop` to the top level of your CloudFormation template.

Add a String type Parameter to pass in your Base64 encoded JSON Object. Each Entry in this mapping will be used to create a resource for the Resource definition. If the Json object is empty, no resources will be created. Values in the Object will be passed into the template for use in the resource definition.

The Resource Name will always be the objectname in the JsonObject, it must be a valid CloudFormation Resource Name, otherwise the transform will fail.



### References of Ref and Arn Usage

Another advanced usage of Base64loop allows you to get the list of resources using the Ref or Fn::GetAtt: <resource>.Arn intrinsic functions. This will return a list preformated to obtain the Ref (usually ID), or the Arn of the resources we have just deployed using a loop.

NOTE: This can also be used on it's own to just import a list as a parameter without deploying the resources.


To get the Arn:

Using ```Base64loopArn: RuleBase64``` on a resource then using the !Base64loopArn

To get the Arn

Using ```Base64loopRef: RuleBase64``` on a resource then using the !Base64loopRef



### Parameter JSON Format

In your template for the resource you want to loop through, use the Base64loop key followed by your parameter name `Base64loop: ResourceListBase64` for example

To get each parameter use the `!Base64loop <paramname>` format

Here is an example:

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Transform: Base64loop

Parameters:
  ResourceListBase64:
    Type: String

Resources:
  TestingBucket:
    Type: AWS::S3::Bucket
    Base64loop: RuleBase64
    Properties:
      BucketName: "!Base64loop name"
```


## Author

[Steven George](https://github.com/steven-geo); AWS Consultant; Electronics Enthusiast
