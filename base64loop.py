""" Cloudformation Macro to iterate through a base64 param like a static mapping """
##pylint: disable=broad-except
import re
import sys
import base64
import traceback
import json
import copy
BASE64LOOP_RE = re.compile(r'(?i)!Base64loop (?P<explode_key>\w+)')

def walk_resource(resource, map_data):
    """ Recursively process a resource. """
    new_resource = {}
    if isinstance(resource, str) and not resource.startswith('!'):
        new_resource = resource
    else:
        for key, value in resource.items():
            newvalue = value
            if isinstance(newvalue, dict):
                new_resource[key] = walk_resource(newvalue, map_data)
            elif isinstance(newvalue, list):
                newvalue = []
                for listitem in value:
                    newvalue.append(walk_resource(listitem, map_data))
            elif isinstance(newvalue, str):
                match = BASE64LOOP_RE.search(newvalue)
                while match:
                    explode_key = match.group('explode_key')
                    try:
                        replace_value = map_data[explode_key]
                    except KeyError:
                        print(f"Missing {explode_key} in mapping while processing {key}: {value}")
                    if isinstance(replace_value, (int, list)):
                        newvalue = replace_value
                        match = None
                    else:
                        newvalue = newvalue.replace(match.group(0), replace_value)
                        match = BASE64LOOP_RE.search(newvalue)
                new_resource[key] = newvalue
            else:
                new_resource[key] = newvalue
    return new_resource

def list_resource(resource, map_data):
    """ Replaces a list identifier with list of resource names we looped through"""
    new_resource = {}
    if not isinstance(resource, str):
        for key, value in resource.items():
            newvalue = value
            if isinstance(value, dict):
                newvalue = list_resource(value, map_data)
            elif isinstance(value, list):
                newvalue = []
                for listitem in value:
                    newvalue.append(list_resource(listitem, map_data))
            elif isinstance(value, str):
                if value == "!Base64loopArn":
                    newvalue = []
                    for loopresource in map_data:
                        newvalue.append({"Fn::GetAtt": f"{loopresource}.Arn"})
                elif value == "!Base64loopRef":
                    rlist = []
                    for loopresource in map_data:
                        rlist.append({"Ref": f"{loopresource}"})
                    newvalue = rlist
            new_resource[key] = newvalue
    else:
        new_resource = resource
    return new_resource

def decode_param(base64_data):
    """ Gets the param data from Base64 into a Json dict"""
    try:
        string_data = base64.b64decode(base64_data).decode('utf8')
        explode_map_data = json.loads(string_data)
    except Exception as error:
        print(f"Error Loading Base64 Data: {error}")
        raise
    return explode_map_data

def handle_transform(template, paramvalues):
    """Go through template and explode resources."""
    # Process Runtime Paramater Values
    usedparams = copy.deepcopy(template['Parameters'])
    for param in usedparams:
        if param in paramvalues:
            usedparams[param]['Default'] = paramvalues[param]
    # Process Template Resources
    new_resources = {}
    for resource_name, resource in template['Resources'].items():
        if 'Base64loopArn' in resource:
            # Looping resource from out map data
            base64loop_str = resource['Base64loopArn']
            del resource['Base64loopArn']
            print(f"Base64loopArn Item Found: {resource_name}")
            maptype = "ArnList"
        elif 'Base64loopRef' in resource:
            # Looped Resources as a List of Ref:
            base64loop_str = resource['Base64loopRef']
            del resource['Base64loopRef']
            print(f"Base64loopRef Item Found: {resource_name}")
            maptype = "RefList"
        elif 'Base64loop' in resource:
            # Looped Resources as a List of Fn::GetAtt
            base64loop_str = resource['Base64loop']
            del resource['Base64loop']
            print(f"Base64loop Item Found: {resource_name}")
            maptype = "Loop"
        else:
            # No Transformation required on this resource
            new_resources[resource_name] = resource
            continue
        try:
            explode_map_data = decode_param(usedparams[base64loop_str]['Default'])
        except KeyError:
            # resource refers to a mapping entry which doesn't exist, so fail
            print(f"Unable to find mapping for Base64loop resource {resource_name}")
            raise
        resource_instances = explode_map_data.keys()
        if maptype == "Loop":
            for resource_instance in resource_instances:
                new_resource = walk_resource(resource, explode_map_data[resource_instance])
                new_resource_name = resource_instance
                new_resources[new_resource_name] = new_resource
        if maptype in ('ArnList', 'RefList'):
            resourcelist = []
            for resource_instance in resource_instances:
                resourcelist.append(resource_instance)
            new_resource = list_resource(resource, resourcelist)
            new_resources[resource_name] = new_resource
    template['Resources'] = new_resources
    return template

def handler(event, _context):
    """Handle invocation in Lambda (when CloudFormation processes the Macro)"""
    fragment = event["fragment"]
    status = "success"
    error_message = "none"
    try:
        fragment = handle_transform(event["fragment"],event["templateParameterValues"])
        print(f"output_template={fragment}")
    except Exception as error:
        print("FAILURE: {error}")
        error_message = error
        print(traceback.format_exc())
        status = "failure"
    return {
        "requestId": event["requestId"],
        "status": status,
        "fragment": fragment,
        "errorMessage": error_message
    }

if __name__ == "__main__":
    # If run from the command line, functions like !GetAtt or !Ref will
    # cause a constructor error. Use alternative annotation like
    # Fn::GetAtt: or Ref: instead.
    if len(sys.argv) == 2:
        filename = sys.argv[1]
        if filename.endswith(".yml") or filename.endswith(".yaml"):
            try:
                import yaml
            except ImportError:
                print("Please install PyYAML to test yaml templates")
                sys.exit(1)
            with open(filename, 'r', encoding="utf-8") as file_handle:
                loaded_fragment = yaml.safe_load(file_handle)
        elif filename.endswith(".json"):
            with open(sys.argv[1], 'r', encoding="utf-8") as file_handle:
                loaded_fragment = json.load(file_handle)
        else:
            print("Test file needs to end .yaml, .yml or .json")
            sys.exit(1)
        cmdlineparams = {}  # FUTURE: Handle Params on the command line
        new_fragment = handle_transform(loaded_fragment, cmdlineparams)
        print(json.dumps(new_fragment, indent=4, sort_keys=True, default=str))
