# Alex Nersessian 3/30/22
import getpass
import time
import requests
import urllib3
urllib3.disable_warnings()


def get_auth_token(env):
    url = f'{env["base_url"]}/dna/system/api/v1/auth/token'
    auth_headers = {
        "Content-Type": "application/json"
    }

    # Make the POST Request
    try:
        response = requests.request("POST", url, auth=(env['username'], env['password']), headers=auth_headers, verify=False)
        print(response.status_code)
        if response.status_code == 401:
            for i in range(3):
                password = getpass.getpass()
                response = requests.request("POST", url, auth=(env['username'], password), headers=auth_headers,
                                            verify=False)

                if response.status_code == 200:
                    break

        if response.status_code == requests.codes.ok:
            token = response.json()["Token"]
            return token

    except:
        print("Issue with credentials!")


def get_device_info_by_id(env, dev_id):
    url = f'{env["base_url"]}/dna/intent/api/v1/network-device/{dev_id}/'

    headers = {
        'x-auth-token': env['token'],
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    response = requests.request("GET", url, headers=headers, verify=False)

    return response.json()


def create_tag(env, name):
    url = f'{env["base_url"]}/dna/intent/api/v1/tag'

    headers = {
        'x-auth-token': env['token'],
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    payload = {"name": name}

    response = requests.request("POST", url, headers=headers, json=payload, verify=False)

    return response.status_code


def tag_add_member(env, tag_id, members):
    url = f'{env["base_url"]}/dna/intent/api/v1/tag/{tag_id}/member'
    #print(tagId)
    #print()
    #print(members)
    headers = {
        'x-auth-token': env['token'],
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    payload = {"networkdevice": members}

    response = requests.request("POST", url, headers=headers, json=payload, verify=False)

    return response.status_code


def get_tag_id(env, name):
    url = f'{env["base_url"]}/dna/intent/api/v1/tag'

    headers = {
        'x-auth-token': env['token'],
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    params = {'name': name}

    response = requests.request("GET", url, headers=headers, params=params, verify=False)

    return response.json()['response'][0]['id']


def get_device_tags(env):
    url = f'{env["base_url"]}/dna/intent/api/v1/tag'

    headers = {
        'x-auth-token': env['token'],
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    tags = []
    response = requests.request("GET", url, headers=headers, verify=False)

    for item in response.json()['response']:
        tags.append(item)

    return tags


def get_devices_by_tag(env, tag_id):
    url = f'{env["base_url"]}/dna/intent/api/v1/tag/{tag_id}/member?memberType=networkdevice'
    dev_list = []
    headers = {
        'x-auth-token': env['token'],
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    devices = []
    response = requests.request("GET", url, headers=headers, verify=False)
    for item in response.json()['response']:
        devices.append(item)

    for item in response.json()['response']:
        dev_list.append({'hostName': item['hostname'], 'type': 'MANAGED_DEVICE_UUID',
                        'id': item['instanceUuid']})  # structure the list to the format of targetInfo

    return dev_list


def get_devices_by_platform(env, platform_Id):
    url = f'{env["base_url"]}/dna/intent/api/v1/network-device'
    headers = {
        'x-auth-token': env['token'],
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    dev_list = []
    query_string_params = platform_Id  # GET Target Devices from env file
    response = requests.get(url, headers=headers,
                            params=query_string_params, verify=False)
    for item in response.json()['response']:
        dev_list.append({'hostName': item['hostname'], 'type': 'MANAGED_DEVICE_UUID',
                        'id': item['id']})  # structure the list to the format of targetInfo

    return dev_list


# Get list of all DNAC inventory
def get_network_devices(env):
    offset = 1
    limit = 500  # Do NOT exceed 500 as the limit (Per DNAC documentation)
    device_list = []

    headers = {
        "content-type": "application/json",
        "Accept": "application/json",
        "x-auth-token": env['token']
    }

    try:
        while True:
            # Make the GET Request
            url = f"{env['base_url']}/dna/intent/api/v1/network-device?offset={offset}&limit={limit}"
            response = requests.request("GET", url, headers=headers, verify=False)

            if response.status_code == 401:
                token = get_auth_token(env)
                offset -= limit
                headers = {
                    "content-type": "application/json",
                    "Accept": "application/json",
                    "x-auth-token": token
                }
                response = requests.request("GET", url, headers=headers, verify=False)  # remake request that failed

            if response.json()['response'] and response.status_code != 401:
                device_list.extend(response.json()['response'])
                offset += limit
            else:
                break

        return device_list  # return the list of dnac devices

    except Exception as e:
        print(e)
        return


def get_device_id(env, name):
    dev_list = []
    url = f'{env["base_url"]}/dna/intent/api/v1/device-detail'
    headers = {
        'x-auth-token': env['token'],
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    for device in name:
        #print(device[0])
        params = {'searchBy': device[0], 'identifier': 'nwDeviceName'}
        dev = requests.get(url, headers=headers, params=params, verify=False)
        #print(dev.json())
        dev_list.append(dev.json()['response']["nwDeviceId"])
    #print(dev_list)
    return dev_list


def get_project_names(env):
    url = f"{env['base_url']}/dna/intent/api/v1/template-programmer/template"
    headers = {
        "x-auth-token": env["token"],
        "Content-Type": "application/json",
    }

    response = requests.request("GET", url, headers=headers, verify=False)
    project = []

    for line in response.json():
        if line['projectName'] not in project:
            project.append(line['projectName'])

    return project


def get_template_id(env, project):
    url = f"{env['base_url']}/dna/intent/api/v1/template-programmer/template"
    template = []
    headers = {
        "x-auth-token": env["token"],
        "Content-Type": "application/json",
    }

    response = requests.request("GET", url, headers=headers, verify=False)

    # print(json.dumps(response.json(), indent=4))
    for line in response.json():
        if project in str(line):  # Get template ID from desired project
            template.append(dict(line)['name'])
            template.append(dict(line)['templateId'])

    return template


def deploy_template(env, template_id, devices):
    url = f"{env['base_url']}/dna/intent/api/v1/template-programmer/template/deploy"
    headers = {
        "x-auth-token": env["token"],
        "Content-Type": "application/json",
    }

    # devices = json.loads(get_Devices_By_Platform(env))
    payload = {
        "forcePushTemplate": True,
        "targetInfo": devices,  # within this variable we can pass up to 100 devices to be provisioned in one job
        "templateId": template_id
    }

    # Make POST request
    response = requests.post(url, headers=headers, json=payload, verify=False)

    deploy_id = response.json().get('deploymentId').split()[-1]

    return deploy_id


def get_task(env, task_id):
    url = f"{env['base_url']}/dna/intent/api/v1/task/{task_id}"
    headers = {
        "x-auth-token": env["token"],
        "Content-Type": "application/json",
    }

    # Make GET request
    response = requests.get(url, headers=headers, verify=False)

    return response.json()  # return response with information about specific task


# Need a way to check if deployment of template to device was successful
def check_deployment_status(env, deployment_id):
    url = f"{env['base_url']}/dna/intent/api/v1/template-programmer/template/deploy/status/{deployment_id}"
    headers = {
        "x-auth-token": env["token"],
        "Content-Type": "application/json",
    }

    # Make GET request
    response = requests.get(url, headers=headers, verify=False)
    # pprint.pprint(response.json())

    return response.json()["devices"]  # return the deployment status


# Distribute images to devices
def image_distribution(env, uuid_list, image_id, batch_size):
    # Do Not set batch size to greater than 40 or performance will significantly drop on DNAC. Better to keep at ~20.
    body = []
    batches = []
    task_id_list = []
    url = env['base_url'] + "/dna/intent/api/v1/image/distribution"

    # Define the headers
    headers = {
        "content-type": "application/json",
        "Accept": "application/json",
        "x-auth-token": env["token"]
    }

    for i, dev_id in enumerate(uuid_list, 1):  # start from 1
        # Build body with batch of devices that distribution is being executed on.
        body.append({
            "deviceUuid": dev_id,
            "imageUuid": image_id
        })

        if i % batch_size == 0:  # if we hit batch size start new batch.
            batches.append(body)
            body = []

    if body:
        batches.append(body)

    for batch in batches:
        response = requests.post(url, headers=headers, json=batch, verify=False)

        if response.status_code == 401:
            token = get_auth_token(env)
            headers = {
                "content-type": "application/json",
                "Accept": "application/json",
                "x-auth-token": token
            }
            response = requests.post(url, headers=headers, json=batch, verify=False)
            task_id_list.append(response.json()["response"]["taskId"])

        else:
            task_id_list.append(response.json()["response"]["taskId"])

    return task_id_list


# Activate image on any given device
def image_activation(env, uuid_list, image_id):
    task_list = []

    url = env['base_url'] + "/dna/intent/api/v1/image/activation/device"

    headers = {
        "content-type": "application/json",
        "Accept": "application/json",
        "x-auth-token": env["token"]
    }

    for dev_id in uuid_list:
        body = [{
            "activateLowerImageVersion": True,
            "deviceUuid": dev_id,
            "imageUuidList": [image_id]
        }]

        try:
            response = requests.post(url, headers=headers, json=body, verify=False)
            if response.status_code == 401:
                token = get_auth_token(env)
                headers = {
                    "content-type": "application/json",
                    "Accept": "application/json",
                    "x-auth-token": token
                }
                response = requests.post(url, headers=headers, json=body, verify=False)

            task_list.append(response.json()["response"]["taskId"])
            time.sleep(0.4)  # add small delay to prevent overwhelming DNAC

        except:
            continue

    return task_list


# Get device hostnames with location
def get_devices_from_site_id(env, site_id, target_model_list):
    limit = 1000  # Do NOT set over 1000 as per DNAC documentation.
    offset = 1
    device_list = []
    dev_type_list =[]
    ip_dev_dict = {}

    # Define the new headers
    headers = {
        "content-type": "application/json",
        "Accept": "application/json",
        "x-auth-token": env['token']
    }

    while True:
        url =  f"{env['base_url']}/dna/intent/api/v1/device-health?siteId={site_id}&limit={limit}&offset={offset}"
        offset += limit
        # Get the network device JSON
        response = requests.get(url, headers=headers, verify=False)

        if not response.json()["response"]:
            break

        device_list.extend(response.json()["response"])


    return device_list


# Gets task details given a task id.
def get_task_detail(env, task_id):
    headers = {
        "content-type": "application/json",
        "Accept": "application/json",
        "x-auth-token": env['token']
    }

    response = requests.get(f"{env['base_url']}/api/v1/image/task?taskUuid={task_id}",
                            headers=headers, verify=False)

    if response.status_code == 401:
        token = get_auth_token(env)
        headers = {
            "content-type": "application/json",
            "Accept": "application/json",
            "x-auth-token": token
        }
        response = requests.get(f"{env['base_url']}/api/v1/image/task?taskUuid={task_id}", headers=headers, verify=False)

    return response.json()["response"]

