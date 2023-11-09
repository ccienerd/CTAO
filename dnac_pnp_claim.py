__author__ = "Saurabh Sharma & Alexios Nersessian"
__credits__ = ["Saurabh & Alexios"]
__email__ = "saushar2@cisco.com"
__version__ = "1.0"

import getpass
from csv import DictReader
import requests
import urllib3

urllib3.disable_warnings()


# DNAC uses basic auth and a short-lived token is used for making API calls
def get_auth_token(base_url, username, password):
    try:
        url = f'{base_url}/dna/system/api/v1/auth/token'
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

        # Make the POST Request to get a Token
        response = requests.post(url, auth=(username, password), headers=headers, verify=False)

        if response.status_code == 401 or response.status_code == 403:
            print()
            print("Issue with credentials!")
            print()

            return

        # Validate Response
        if 'error' in response.json():
            print()
            print('ERROR: Failed to retrieve Access Token!')
            print(f"REASON: {response.json()['error']}")

        else:
            return response.json()['Token']  # return only the token

    except Exception as e:
        print(e)
        return


def get_credential_ids(base_url, token):
    # ["CLI", "SNMPV2_READ_COMMUNITY", "SNMPV2_WRITE_COMMUNITY", "SNMPV3", "HTTP_WRITE", "HTTP_READ", "NETCONF"]
    cred_type = ["CLI", "SNMPV3"]  # Cap1 only uses these 2
    response = []

    headers = {
        'x-auth-token': token,
        'Accept': 'application/json'
    }

    for cred in cred_type:
        url = f"https://{base_url}/dna/intent/api/v1/global-credential?credentialSubType={cred}"
        # print(url)
        resp = requests.request("GET", url, headers=headers, verify=False).json()["response"]

        for item in resp:
            response.append(item["id"])

    return response


# readserialnumber
def read_sn_csv(file_name):
    sn_list = {}
    with open(file_name, 'r') as inventory:
        csv_dict_reader = DictReader(inventory)

        for device in csv_dict_reader:
            sn_list[device["Serial Number"]] = device["Hostname"]

    return sn_list


def claim_site_pnp(base_url, token, deviceid, siteid, hostname):
    endpoint = "/api/v1/onboarding/pnp-device/site-claim"

    headers = {
        'x-auth-token': token,
        'Accept': 'application/json'
    }
    body = {
        "siteId": siteid,
        "deviceId": deviceid,
        "hostname": hostname,
        "type": "Default",
        "imageInfo": {
            "imageId": "",
            "skip": False,
            "removeInactive": True
        },
        "configInfo": {
            "configId": "",
            "configParameters": []
        }
    }

    response = requests.request("POST", url=base_url + endpoint, headers=headers, json=body, verify=False)
    print(response.status_code)
    print(response.text)
    return response.json()


def claim_device_pnp(base_url, token, deviceid,  hostname, template_id, image_id=None):
    endpoint = "/api/v1/onboarding/pnp-device/claim"

    headers = {
        'x-auth-token': token,
        'Accept': 'application/json'
    }

    body = {
        "populateInventory": True,
        "deviceClaimList": [
            {
                "deviceId": deviceid,
                "configList": [
                    {
                        "configParameters": [],
                        "configId": template_id,
                        "saveToStartup": True
                    }
                ],
                "hostname": hostname
            }
        ],
        "imageId": image_id,
        "removeInactive": False,
        "configId": template_id  #"bdaec676-5448-4b36-94c2-0145d129635a"
    }

    response = requests.request("POST", url=base_url + endpoint, headers=headers, json=body, verify=False)
    return response.json()


def get_device_id(base_url, token):
    endpoint = "/dna/intent/api/v1/onboarding/pnp-device"
    headers = {
        'x-auth-token': token,
        'Accept': 'application/json'
    }

    response = requests.request("GET", url=base_url + endpoint, headers=headers, verify=False)
    return response.json()


def get_sites(base_url, token):
    endpoint = "/dna/intent/api/v1/site"

    headers = {
        'x-auth-token': token,
        'Accept': 'application/json'
    }

    response = requests.request("GET", url=base_url + endpoint, headers=headers, verify=False)
    return response.json()["response"]


def sn_to_id(device_ids):
    dev_sn_to_id = {}

    for dev in device_ids:
        #print(dev["deviceInfo"]['serialNumber'], dev["id"])
        dev_sn_to_id[dev["deviceInfo"]['serialNumber']] = dev["id"]

    return dev_sn_to_id


def list_of_sites(data):
    site_dict = {}
    for i, site in enumerate(data):

        if site["additionalInfo"]:
            for lookup in site["additionalInfo"]:
                if lookup["attributes"].get("type") and (lookup["attributes"].get("type") == "building" or lookup["attributes"].get("type") == "floor"):
                    site_dict[site["siteNameHierarchy"]] = site["id"]

    return list(site_dict.items())


def site_selection_menu(site_list):
    selected_site = {}
    print("************ List of sites ************")
    for i, site in enumerate(site_list, 1):
        print(i, site)

    print()
    while True:
        try:
            choice = input(f"Please select a site 1-{len(site_list)}: ")
            selected_site = site_list[int(choice) - 1]
            print(selected_site)
            break

        except:
            print("Invalid Choice!")

    return selected_site


def get_device_list_ready_to_claim(base_url, token):
    headers = {
        'x-auth-token': token,
        'Accept': 'application/json'
    }

    endpoint = "/api/v1/onboarding/pnp-device?state=Unclaimed%2CPlanned&offset=0&limit=1000"

    response = requests.request("GET", url=base_url + endpoint, headers=headers, verify=False)
    return response.json()


def main():
    base_url = "https://10.8.6.56"
    username = "admin"
    password = getpass.getpass("Enter DNAC password:  ")
    unc_dev_list = []

    # 1. Read SN list from CSV
    sn_dict = read_sn_csv("sn_list.csv")

    # 2. Get DNAC Auth Token
    token = get_auth_token(base_url, username, password)

    # 3. Get Device ID ready to be claimed
    #device_ids = get_device_id(base_url, token)
    unclaimed_devs = get_device_list_ready_to_claim(base_url, token)

    # 4. create SN to ID mapping
    sn_to_id_dict = sn_to_id(unclaimed_devs)

    for dev in unclaimed_devs:
        unc_dev_list.append(dev.get('deviceInfo').get('serialNumber'))

    intersection = list(set(unc_dev_list) & set(list(sn_dict.keys())))

    print("List of Devices ready to be claimed", len(intersection), "out of", len(sn_dict), "provided.")
    for valid_sn in intersection:
        print(valid_sn)

    print()

    # 5. Get sites
    raw_sites = get_sites(base_url, token)

    site_list = list_of_sites(raw_sites)
    selected_site = site_selection_menu(site_list)

    # 6. Start Discovery
    for sn, hostname in sn_dict.items():
        if sn in intersection:
            claim_site_pnp(base_url, token, sn_to_id_dict[sn], selected_site[1], hostname)
            print()
        else:
            print(sn, "cannot be claimed! It is not in then list of unclaimed devices.")
            print()

    print("Done!")


if __name__ == "__main__":
    main()
