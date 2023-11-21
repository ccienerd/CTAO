__author__ = "Alexios Nersessian"
__copyright__ = "Copyright 2023, Cisco"
__email__ = "anersess@cisco.com"
__version__ = "v3"
__coauthor__ = "Saurabh Sharma"

"""
Script distributes and activates an image on any given device list. The device list is provided as a CSV file. 

usage example:  python distribute_activate_images.py -d test_distro.csv -i 644716c3-4524-4e50-ae94-0fd2e5c1d076 -u "https://www.dnac-example.com" --distribute --activate
"""

import csv
import os
import argparse
import getpass
import time
import requests
import urllib3

urllib3.disable_warnings()

# Global vars
username = ""
password = ""
token = ""

# Initialize Arg parser
arg_parser = argparse.ArgumentParser(prog=__doc__)

arg_parser.add_argument(
    "-d",
    "--devices",
    required=True,
    type=str,
    help="File with all hostnames. Must be a csv file."
)

arg_parser.add_argument(
    "-i",
    "--image",
    required=True,
    type=str,
    help="Image uuid."
)

arg_parser.add_argument(
    "--activate",
    action="store_true",
    help="Activate Image"
)

arg_parser.add_argument(
    "--distribute",
    action="store_true",
    help="Distribute Image"
)

arg_parser.add_argument(
    "-u",
    "--url",
    required=True,
    type=str,
    help="DNAC URL. eg https://www.dnac-example.com"
)

args = vars(arg_parser.parse_args())


# Create a function to get the authorization token
def get_auth_token(url):
    global username
    global password

    if not username or not password:
        username = input("Enter username:  ")
        password = getpass.getpass()

    # Concatenate the URL variable with the path to get the token
    auth_url = url + "/dna/system/api/v1/auth/token"

    # Include the proper content-type field here
    auth_headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.request("POST", auth_url, auth=(username, password), headers=auth_headers, verify=False)
        print(response.status_code)
        if response.status_code == 401:
            for i in range(3):
                password = getpass.getpass()
                response = requests.request("POST", auth_url, auth=(username, password), headers=auth_headers,
                                            verify=False)

                if response.status_code == 200:
                    break

        if response.status_code == requests.codes.ok:
            token = response.json()["Token"]
            with open("token.tk", "w") as t:
                t.write(response.json()["Token"])
            return token

    except Exception as e:
        print(e)
        print("Issue with credentials!")


# minimal API call to test validity of a DNAC token
def test_connection(base_url):
    url = base_url + "/dna/intent/api/v1/diagnostics/system/health"

    headers = {
        "content-type": "application/json",
        "Accept": "application/json",
        "x-auth-token": token
    }

    response = requests.request("GET", url, headers=headers, verify=False)

    return response.status_code


# Get list of all DNAC inventory
def get_network_devices(base_url):
    global token
    offset = 1
    limit = 500  # Do NOT exceed 500 as the limit (Per DNAC documentation)
    device_list = []

    headers = {
        "content-type": "application/json",
        "Accept": "application/json",
        "x-auth-token": token
    }

    try:
        while True:
            # Make the GET Request
            url = f"{base_url}/dna/intent/api/v1/network-device?offset={offset}&limit={limit}"
            response = requests.request("GET", url, headers=headers, verify=False)

            if response.status_code == 401:
                token = get_auth_token(base_url)
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


# Distribute images to devices
def image_distribution(base_url, uuid_list, image_id, batch_size):
    # Do Not set batch size to greater than 40 or performance will significantly drop on DNAC. Better to keep at ~20.
    global token
    body = []
    batches = []
    task_id_list = []
    url = base_url + "/dna/intent/api/v1/image/distribution"

    # Define the headers
    headers = {
        "content-type": "application/json",
        "Accept": "application/json",
        "x-auth-token": token
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
            token = get_auth_token(base_url)
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
def image_activation(base_url, uuid_list, image_id):
    global token
    task_list = []

    url = base_url + "/dna/intent/api/v1/image/activation/device"

    headers = {
        "content-type": "application/json",
        "Accept": "application/json",
        "x-auth-token": token
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
                token = get_auth_token(base_url)
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


# Load inventory of devices from a given csv
def get_devices_from_csv(file):
    with open(file, "r") as f:
        devs = f.read().splitlines()

    return devs


# Create a list of UUIDs given a list of grouped hostnames (model group) and a dict that has uuid info for every device.
def group_by_model_uuid(host_list, all_devs_dict):
    uuid_list = []
    for hostname in host_list:
        try:
            uuid_list.append(all_devs_dict[hostname])

        except:
            continue

    return uuid_list


# Returns 2 lists; list of hostnames and list of uuids of failed devices.
def get_failed_devices(results):
    failed_hostnames = []
    failed_uuids = []

    for device in results:
        if device["taskStatus"] != "success":
            failed_hostnames.append([device["hostName"], device["taskStatus"]])
            failed_uuids.append(device["deviceId"])
            #print(device["hostName"], device["taskStatus"])

    return failed_hostnames, failed_uuids


# Gets task details given a task id.
def get_task_detail(base_url, task_id):
    global token
    headers = {
        "content-type": "application/json",
        "Accept": "application/json",
        "x-auth-token": token
    }

    response = requests.get(f"{base_url}/api/v1/image/task?taskUuid={task_id}",
                            headers=headers, verify=False)

    if response.status_code == 401:
        token = get_auth_token(base_url)
        headers = {
            "content-type": "application/json",
            "Accept": "application/json",
            "x-auth-token": token
        }
        response = requests.get(f"{base_url}/api/v1/image/task?taskUuid={task_id}", headers=headers, verify=False)

    return response.json()["response"]


# Gets a task overall summary given the task id.
def get_overall_task_status(base_url, task_id):
    global token
    block = u'\u2588'
    progress = 0
    headers = {
        "content-type": "application/json",
        "Accept": "application/json",
        "x-auth-token": token
    }

    while True:
        response = requests.get(f"{base_url}/dna/intent/api/v1/task/{task_id}",
                                headers=headers, verify=False)

        if response.status_code == 401:
            token = get_auth_token(base_url)
            headers = {
                "content-type": "application/json",
                "Accept": "application/json",
                "x-auth-token": token
            }
            response = requests.get(f"{base_url}/dna/intent/api/v1/task/{task_id}",
                                    headers=headers, verify=False)

        if response.json()["response"]["progress"] == "Starting Distribution":
            if progress == 0:
                print(" Starting Distribution..")

            progress += 1
            print(f"\r {response.json()['response']['data']} in progress:{block * progress}", end='', flush=True)

            if progress == 20:
                progress = 0
            #print(f" Still Waiting for {response.json()['response']['data']} of images to finish. Please wait..")
            time.sleep(20)
            continue

        elif response.json()["response"]["progress"] == "image activation":
            print(" Starting Image Activation..")
            time.sleep(30)
            continue

        task = response.json()["response"]["progress"].split(',')

        success = int(task[0].split('=')[-1])
        failure = int(task[1].split('=')[-1])
        running = int(task[2].split('=')[-1])
        pending = int(task[3].split('=')[-1])
        total = int(task[-1].split('=')[-1])

        if running == 0 and pending == 0:
            result_dict = {"Success": success, "Failure": failure, "Running": running, "Pending": pending,
                           "Total": total}
            # print(f" Finished {response.json()['response']['data']} job.")
            # print(" Success:", success)
            # print(" Failure:", failure)
            # print(" Running:", running)
            # print(" Pending:", pending)
            # print(" Total:", total)
            # print()
            break
        else:
            progress += 1
            print(f"\r {response.json()['response']['data']} in progress:{block * progress}", end='', flush=True)

            if progress == 20:
                progress = 0
            #print(f" Still Waiting for {response.json()['response']['data']} of images to finish. Please wait..")
            time.sleep(20)

    print()
    return result_dict


# Write to a csv file.
def write_to_csv(dev_list, log_dir, file_name, header, nested=False):

    if not os.path.exists(os.path.join(log_dir + "/SWIM_Jobs")):
        os.makedirs(os.path.join(log_dir + "/SWIM_Jobs"))

    with open(log_dir + "/SWIM_Jobs" + f"/{file_name}.csv", 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([header])

        if not nested:
            #for dev in dev_list:
            writer.writerows(dev_list)
        else:
            for dev in dev_list:
                writer.writerow([dev])


# Defines the workflow of the application.
def main():
    global username
    global password
    global token

    url = args["url"]
    model_list = []
    all_dev_dict = {}
    image_id = args["image"]
    current_timestamp = time.strftime('%m-%d-%Y-%H_%M_%S')  # USA Date Format
    log_dir = "DNAC_SWIM"
    uuid_list = []
    failed_uuids = []
    failed_hostnames = []

    if not args["distribute"] and not args["activate"]:
        print("You have not selected whether you want the script to distribute, activate or carry out both tasks.")
        print()
        return

    # 1) Get DNAC x-auth-token
    print("1. Getting DNAC Token.")

    if os.path.exists("token.tk"):
        with open("token.tk", "r") as t:
            token = t.read()

        #print(token)
        status_code = test_connection(url)
        if status_code == 401:
            # username = input("Enter username:  ")
            # password = getpass.getpass()
            token = get_auth_token(url)

    else:
        token = get_auth_token(url)

    if not token:
        print("Could not get token. Goodbye..")
        exit(1)

    if args["distribute"]:
        # 2) Get All network devices in DNAC
        print(f"2. Getting all devices in DNAC.")
        all_network_devices = get_network_devices(url)

        # 3) Get all network device types
        print("3. Getting all network device types/models in inventory.")
        for device in all_network_devices:
            if device["type"] not in model_list:
                model_list.append(device["type"])

        print(" Global device list:", model_list)

        # 4) Get hostname list from CSV
        print("4. Getting device hostnames from CSV.")
        hostname_list = get_devices_from_csv(args["devices"])

        # print(" Hostnames: ", hostname_list[1:])

        # 5) Create global device dict where we will use to map the hostname of a device to its UUID.
        print("5. Creating Dictionary mapping for hostnames to uuids for all devices.")

        for device in all_network_devices:
            all_dev_dict[device["hostname"]] = device["id"]
        # print("Hostname to uuid mappings", all_dev_dict)

        # 6) Group the device uuids from the specific site by their model and by a filter applied to the hostname.
        print("6. Comparing hostname list to all device dictionary to pull uuids only for our specified hostnames.")
        uuid_list = group_by_model_uuid(hostname_list[1:], all_dev_dict)

        # 7) Distribute Images to devices
        print("7. Distributing images to devices.")

        # 30 devices per API call
        task_info = image_distribution(url, uuid_list, image_id, batch_size=30)
        print()
        print(" Task information: ", task_info)
        print()

        # 8) Validate state of image push job
        print("8. Getting Overall result. This will take a while, you may want to grab some coffee..")

        # Keep count of success, fail and total distributions.
        success = 0
        failure = 0
        total = 0

        for x, task in enumerate(task_info):
            # result = {"Success": 3, "Failure": 1, "Running": 0, "Pending": 0, "Total": 4}
            result = get_overall_task_status(url, task)
            success += result["Success"]
            failure += result["Failure"]
            total += result["Total"]

            # 9) See if there are any failures on any devices
            if x == 0:
                print("9. Getting details on failed devices.")

            if result["Failure"] > 0:
                print(" Failed devices found, getting details.")
                failed = get_task_detail(url, task)  # return response object
                fail_list = get_failed_devices(failed)
                failed_uuids.extend(fail_list[1])
                failed_hostnames.extend(fail_list[0])

        if failed_uuids:
            for failed_id in failed_uuids:  # Remove failed devices from list of uuids to be activated later on
                uuid_list.remove(failed_id)
            write_to_csv(failed_hostnames, log_dir, "Failed_Distributions_" + current_timestamp, header="Failed Devices")

        print()
        print(" Status of image distribution.")
        print(" Successful Devices:", success)
        print(" Failed Devices:", failure)
        print(" Total Devices:", total)
        print()

        print(uuid_list)
        # Write to fileuuids of devices that are ready to be activated
        write_to_csv(uuid_list, log_dir, "UUIDS_to_Activate", "Device UUIDs", True)
        print()

    # 10) Activate images on devices
    failed_activations = []
    if args["activate"]:
        if args["distribute"]:
            print("10. Activating Images")
        else:
            print("2. Activating Images")
        if not uuid_list:  # If uuid list does not exist in RAM then read from csv file.
            uuid_list = get_devices_from_csv(log_dir+"/SWIM_Jobs/UUIDS_to_Activate.csv")
            uuid_list.remove("Device UUIDs")  # Remove header from CSV.

        task_list = image_activation(url, uuid_list, image_id)
        print(" Activation task ids: ", task_list)

        # Keep tally count of success, fail and total activations.
        success = 0
        failure = 0
        total = 0

        for task in task_list:
            activation_task_result = get_overall_task_status(url, task)
            success += activation_task_result["Success"]
            failure += activation_task_result["Failure"]
            total += activation_task_result["Total"]

            if activation_task_result["Failure"] > 0:
                failed_act = get_task_detail(url, task)
                fail_act = get_failed_devices(failed_act)
                failed_activations.append(fail_act[0][0])

                #failed_uuids = failed_act[1]  # Figure out if you want these for later on

        if failed_activations:
            write_to_csv(failed_activations, log_dir, "Failed_Activations_"+current_timestamp, header="Failed Activations")
    
        print(" Status of image activation.")
        print(" Successful Devices:", success)
        print(" Failed Devices:", failure)
        print(" Total Devices:", total)
        print()

    print()
    print("Done! Check /DNAC_SWIM/SWIM_Jobs/ directory for reporting.")
    print()


if __name__ == '__main__':
    main()

 
