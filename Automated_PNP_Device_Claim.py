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
    var_list = {}
    with open(file_name, 'r') as inventory:
        csv_dict_reader = DictReader(inventory)

        for device in csv_dict_reader:
            sn_list[device["Serial Number"]] = device["Hostname"]
            var_list[device["Serial Number"]] = [device["VLAN"], device["MGMT IP"], device["VLAN IP"], device["Site"]] #[vlan, mgmt_ip, vlan_ip]

    return sn_list, var_list


def claim_site_pnp(base_url, token, deviceid, hostname, variables, template_id=None):
    endpoint = "/api/v1/onboarding/pnp-device/site-claim"

    headers = {
        'x-auth-token': token,
        'Accept': 'application/json'
    }
    body = {
        "siteId": variables[3],
        "deviceId": deviceid,
        "hostname": hostname,
        "type": "Default",
        "imageInfo": {
            "imageId": "",
            "skip": False,
            "removeInactive": True
        },
        "configInfo": {
            "configId": "e1825fc0-655f-464b-bee0-cfda47c87222",
            "configParameters": [
                {
                    "key": "vlan",
                    "value": variables[0]
                },
                {
                    "key": "name",
                    "value": hostname
                },
                {
                    "key": "mgmt_ip",
                    "value": variables[1]
                },
                {
                    "key": "vlan_ip",
                    "value": variables[2]
                }
            ]
        }
    }  # [vlan, mgmt_ip, vlan_ip]

    response = requests.request("POST", url=base_url + endpoint, headers=headers, json=body, verify=False)
    return response.json()


def claim_device_pnp(base_url, token, deviceid, hostname, template_id, image_id=None):
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
        "configId": template_id  # "bdaec676-5448-4b36-94c2-0145d129635a"
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
        # print(dev["deviceInfo"]['serialNumber'], dev["id"])
        dev_sn_to_id[dev["deviceInfo"]['serialNumber']] = dev["id"]

    return dev_sn_to_id


def list_of_sites(data):
    site_dict = {}
    for i, site in enumerate(data):

        if site["additionalInfo"]:
            for lookup in site["additionalInfo"]:
                if lookup["attributes"].get("type") and (
                        lookup["attributes"].get("type") == "building" or lookup["attributes"].get("type") == "floor"):
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
    password = getpass.getpass("Enter DNAC password: ")
    unc_dev_list = []

    # 1. Read SN list from CSV
    dev_dict = read_sn_csv("device_list.csv")

    # 2. Get DNAC Auth Token
    token = get_auth_token(base_url, username, password)

    # 3. Get Device ID ready to be claimed
    unclaimed_devs = get_device_list_ready_to_claim(base_url, token)

    # 4. create SN to ID mapping
    sn_to_id_dict = sn_to_id(unclaimed_devs)

    for dev in unclaimed_devs:
        unc_dev_list.append(dev.get('deviceInfo').get('serialNumber'))

    intersection = list(set(unc_dev_list) & set(list(dev_dict[0].keys())))

    print("List of Devices ready to be claimed", len(intersection), "out of", len(dev_dict[0]), "provided.")
    for valid_sn in intersection:
        print(valid_sn)

    print()

    # 5. Get sites
    raw_sites = get_sites(base_url, token)

    site_list = list_of_sites(raw_sites)
    print()
    while True:
   
        choice=input(f"Do you want to proceed with claiming these {len(intersection)} devices ? y/n: "  )
        if choice.lower() == "y":
            print("Starting claiming process...")
            break
        elif choice.lower() == "n":
            print("Aborting...")
            return
        else:
            print("Try again by inputing y/n...")

    # 6. Start Discovery
    failed_devices=[]
    for sn, hostname in dev_dict[0].items():
        if sn in intersection:
            for site in site_list:
                if dev_dict[1][sn][3] in site:
                    dev_dict[1][sn][3]=site[1]
            print("Claiming", hostname, sn,)
            claim_site_pnp(base_url, token, sn_to_id_dict[sn], hostname, dev_dict[1][sn]) # [vlan, mgmt_ip, vlan_ip, site]
            print()

        else:
            failed_devices.append(sn)

    print("Devices listed below can't be claimed becuase they are not in the Catalyst Center PnP portal yet..")

    for sn in failed_devices:
       print(sn)
    print()

    print("Done, Monitor claimed devices in Catalyst center PnP Dashboard for progress!")


if __name__ == "__main__":
    main()
