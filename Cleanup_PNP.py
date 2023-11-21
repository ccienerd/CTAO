__author__ = "Saurabh Sharma & Alexios Nersessian"
__credits__ = ["Saurabh & Alexios"]
__email__ = "saushar2@cisco.com"
__version__ = "1.0"

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
        response = requests.request("POST", url, auth=(env['username'], env['password']), headers=auth_headers,
                                    verify=False)
        print(response.status_code)

        if response.status_code == requests.codes.ok:
            token = response.json()["Token"]
            return token

    except:
        print("Issue with credentials!")


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


def delete_device(env, devices):
    url = f"{env['base_url']}/api/v1/inventory/delete/bulk"
    headers = {
        "x-auth-token": env["token"],
        "Content-Type": "application/json",
    }

    response = requests.delete(url, headers=headers, json=devices, verify=False)

    return


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


def main():
    env = {}
    # get Auth token and save in environment variable
    env["base_url"] = "https://10.8.6.56"  # input("DNAC URL eg https://dnac.example.com:  ")
    env["username"] = "admin"
    env["password"] = getpass.getpass()
    env['token'] = get_auth_token(env)

    device_list = get_network_devices(env)
    reset_list = []
    delete_list = []

    print("List of devices available to reset.")
    for i, dev in enumerate(device_list, 1):
        print(i, dev["hostname"], dev["serialNumber"], dev["id"])
        delete_list.append({
            "instanceUuid": dev["id"],
            "cleanConfig": False
        })
        reset_list.append({
            "id": dev["id"],
            "type": "MANAGED_DEVICE_UUID",
        })
    print()

    print("Select devices to reset e.g 1,3,7. Type all to reset all devices.")
    selection = input("Enter choice(s): ")

    if "all" in selection.split(","):
        deploy_template(env, "cb2ff904-054d-4288-afc4-fbd66f0504ea", reset_list)

    else:
        reset_list = []
        delete_list = []

        for index in selection.split(","):
            delete_list.append({
                "instanceUuid": device_list[int(index) - 1]["id"],
                "cleanConfig": False
            })

            reset_list.append(
                {
                    "id": device_list[int(index) - 1]["id"],
                    "type": "MANAGED_DEVICE_UUID",
                }
            )

        deploy_template(env, "cb2ff904-054d-4288-afc4-fbd66f0504ea", reset_list)

    print()
    for i in range(1, 10):
        print("Resetting pnp on devices. Please wait" + "." * i, end='\r', flush=True)
        time.sleep(9)
    print()
    print()

    # DELETE DEVICES
    print("Deleting Devices from inventory.")
    delete_device(env, delete_list)

    print("Done!")


if __name__ == "__main__":
    main()
