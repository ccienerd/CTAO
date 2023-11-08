__author__ = "Saurabh Sharma & Alexios Nersessian"
__credits__ = ["Saurabh & Alexios"]
__email__ = "saushar2@cisco.com"
__version__ = "1.0"

import argparse
import getpass
from csv import DictReader
import requests
import urllib3

urllib3.disable_warnings()

# Initialize Arg parser
arg_parser = argparse.ArgumentParser(prog=__doc__)

arg_parser.add_argument(
    "-i",
    "--ip-ranges",
    required=False,
    type=str,
    default='ip_ranges.csv',
    help="Name of inventory file. Must be a csv file."
)

arg_parser.add_argument(
    "-d",
    "--disco-type",
    required=False,
    type=str,
    default="MULTI RANGE",
    help="Discovery Type, options: RANGE, MULTI RANGE"
)

arg_parser.add_argument(
    "-n",
    "--disco-name",
    required=True,
    type=str,
    help="Give a Unique Name to the discovery job."
)


args = vars(arg_parser.parse_args())


# DNAC uses basic auth and a short-lived token is used for making API calls
def get_auth_token(base_url, username, password):
    try:
        url = f'https://{base_url}/dna/system/api/v1/auth/token'
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
        #print(url)
        resp = requests.request("GET", url, headers=headers, verify=False).json()["response"]

        for item in resp:
            response.append(item["id"])

    return response


# readserialnumber


def read_sn_csv(file_name):
    sn_list = {}
    with open(file_name, 'r') as inventory:
        css_dict_reader = DictReader(inventory)

        for device in csv_dict_reader:
            sn_list[device["List of SNs"]] = device["hostname"]
            

    return sn_list

def claim_device_pnp(base_url,token,deviceid,sn,siteid,hostname):
    endpoint = "/api/v1/onboarding/pnp-device/site-claim"
    
    headers = {
        'x-auth-token': token,
        'Accept': 'application/json'
    }
    Body = {
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

    response = requests.request("POST", url=base_url+endpoint, json=Body, verify=False)
    return response.json()


def get_device_id(base_url, token):
    endpoint = "/dna/intent/api/v1/onboarding/pnp-device"
    headers = {
        'x-auth-token': token,
        'Accept': 'application/json'
    }

    response = requests.request("GET", url=base_url+endpoint, verify=False)
    return response.json()

def get_site_id(base_url,token)
    endpoint ="/dna/intent/api/v1/site"

    headers = {
        'x-auth-token': token,
        'Accept': 'application/json'
    }
    response = requests.request("GET", url=base_url+endpoint, verify=False)
    return response.json()


def main():
    base_url = input("Enter DNAC URL. eg. dnac.cisco.com:  ")
    username = input("Enter Username:  ")
    password = getpass.getpass()

    # 1. Read SN list from CSV
     snlist = read_sn_csv("sn_list.csv")
   # sns_string = ","
    #sns_string = ips_string.join(ips)
    #print(ips_string)

    # 2. Get DNAC Auth Token
    token = get_auth_token(base_url, username, password)
    #print(token)

    # 3. Get Device ID ready to be claimed
    device_ids = get_device_id(base_url, token)
    

    # 4. Start Discovery


    print("Done!")
    print("Check Inventory in DNAC GUI for results.")
    print("Task Id: ", disco_task)
    print()



if __name__ == "__main__":
    main()



