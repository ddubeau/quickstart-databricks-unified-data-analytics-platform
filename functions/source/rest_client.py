# importing the requests library 
import requests 
from requests.exceptions import HTTPError
import cfnresponse
import threading
import logging
import json

def timeout(event, context):
    logging.error('Execution is about to time out, sending failure response to CloudFormation')
    cfnresponse.send(event, context, cfnresponse.FAILED, {}, None)

def handler(event, context):
    # make sure we send a failure to CloudFormation if the function
    # is going to timeout
    timer = threading.Timer((context.get_remaining_time_in_millis()
            / 1000.00) - 0.5, timeout, args=[event, context])
    timer.start()

    print('Received event: %s' % json.dumps(event))
    status = cfnresponse.SUCCESS
    responseData = {}

    try:
        # Do no do anything if requestType is DELETE
        if event['RequestType'] == 'Create':            

            if event['ResourceProperties']['action'] == 'CREATE_CREDS':
                post_result = create_credentials(
                                    event['ResourceProperties']['accountId'],
                                    event['ResourceProperties']['credentials_name'],
                                    event['ResourceProperties']['role_arn'],
                                    event['ResourceProperties']['username'],
                                    event['ResourceProperties']['password']
                                )
                responseData['CredentialsId'] = post_result['credentials_id']
                responseData['ExternalId'] = post_result['aws_credentials']['sts_role']['external_id']

            if event['ResourceProperties']['action'] == 'CREATE_STORAGE_CONFIG':
                post_result = create_storage_config(
                                    event['ResourceProperties']['accountId'],
                                    event['ResourceProperties']['storage_config_name'],
                                    event['ResourceProperties']['s3bucket_name'],
                                    event['ResourceProperties']['username'],
                                    event['ResourceProperties']['password']
                                )
                responseData['StorageConfigId'] = post_result['storage_configuration_id']
            
            if event['ResourceProperties']['action'] == 'CREATE_WORKSPACE':
                post_result = create_workspace(
                                    event['ResourceProperties']['accountId'],
                                    event['ResourceProperties']['workspace_name'],
                                    event['ResourceProperties']['deployment_name'],
                                    event['ResourceProperties']['aws_region'],
                                    event['ResourceProperties']['credentials_id'],
                                    event['ResourceProperties']['storage_config_id'],
                                    event['ResourceProperties']['username'],
                                    event['ResourceProperties']['password']
                                )
                responseData['WorkspaceId'] = get_wrkspc_result['workspace_id']
                responseData['WorkspaceStatus'] = get_wrkspc_result['workspace_status']
                responseData['WorkspaceStatusMsg'] = get_wrkspc_result['workspace_status_message']

            if event['ResourceProperties']['action'] == 'GET_WORKSPACE':
                get_wrkspc_result = get_workspace(
                                        event['ResourceProperties']['accountId'],
                                        event['ResourceProperties']['workspace_id'],
                                        event['ResourceProperties']['username'],
                                        event['ResourceProperties']['password']
                                    )
                responseData['WorkspaceStatus'] = get_wrkspc_result['workspace_status']
                responseData['WorkspaceStatusMsg'] = get_wrkspc_result['workspace_status_message']
        
        else:
            logging.debug('RequestType - {}'.format(event['RequestType']))
        
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
        print(f'HTTP content: {http_err.response.content}')
        status = cfnresponse.FAILED
    except Exception as e:
        logging.error('Exception: %s' % e, exc_info=True)
        status = cfnresponse.FAILED
    finally:
        timer.cancel()
        cfnresponse.send(event, context, status, responseData, None)

# POST - create credentials
def create_credentials(account_id, credentials_name, role_arn, username, password):

    # api-endpoint
    URL = "https://accounts.cloud.databricks.com/api/2.0/accounts/"+account_id+"/credentials"
    
    # Json data
    DATA = {
        "credentials_name": credentials_name, 
        "aws_credentials": {
            "sts_role": {
                "role_arn": role_arn
            }
        }
    }

    response = post_request(URL, DATA, username, password)
    print(response)
    
    # parse response
    credentials_id = response['credentials_id']
    external_id = response['aws_credentials']['sts_role']['external_id']
    print('credentials_id - {}, external_id - {}'.format(credentials_id, external_id))
    return response

# POST - create storage configuration
def create_storage_config(account_id, storage_config_name, s3bucket_name, username, password):
    # api-endpoint
    URL = "https://accounts.cloud.databricks.com/api/2.0/accounts/"+account_id+"/storage-configurations"
    
    # Json data
    DATA = {
        "storage_configuration_name": storage_config_name,
        "root_bucket_info": {
            "bucket_name": s3bucket_name
        }
    }

    response = post_request(URL, DATA, username, password)
    print(response)
    
    # parse response
    storage_configuration_id = response['storage_configuration_id']
    print('storage_configuration_id - {}'.format(storage_configuration_id))
    return response

# POST - create workspace
def create_workspace(account_id, workspace_name, deployment_name, aws_region, credentials_id, storage_config_id, username, password):
    # api-endpoint
    URL = "https://accounts.cloud.databricks.com/api/2.0/accounts/"+account_id+"/workspaces"
    
    # Json data
    DATA = {
        "workspace_name": workspace_name, 
        "deployment_name": deployment_name, 
        "aws_region": aws_region, 
        "credentials_id": credentials_id, 
        "storage_configuration_id": storage_config_id
    }

    response = post_request(URL, DATA, username, password)
    print(response)
    
    # parse response
    workspace_id = response['workspace_id']
    workspace_status = response['workspace_status']
    workspace_status_message = response['workspace_status_message']
    print('workspace_id - {}, status - {}, message - {}'.format(workspace_id, workspace_status, workspace_status_message))
    return response

# GET - get workspace
def get_workspace(account_id, workspace_id, username, password):
    # api-endpoint
    URL = "https://accounts.cloud.databricks.com/api/2.0/accounts/"+account_id+"/workspaces/"+workspace_id

    response = get_request(URL, username, password)
    print(response)

    # parse response
    workspace_status = response['workspace_status']
    workspace_status_message = response['workspace_status_message']
    print('workspace status - {}, msg - {}'.format(workspace_status, workspace_status_message))
    return response
    

# POST request function
def post_request(url, json_data, username, password):
    # sending post request and saving the response as response object
    resp = requests.post(url, json=json_data, auth=(username, password))
    
    # extracting data in json format 
    data = resp.json() 
    
    # If the response was successful, no Exception will be raised
    resp.raise_for_status()
    
    print('Successful POST call!!')
    return data

# GET request function
def get_request(url, username, password):
    # sending get request and saving the response as response object 
    resp = requests.get(url = url, auth=(username, password)) 
    
    # extracting data in json format 
    data = resp.json() 
    
    # If the response was successful, no Exception will be raised
    resp.raise_for_status()
    
    print('Successful GET call!!')
    return data