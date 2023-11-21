__author__ = "Alexios Nersessian"
__copyright__ = "Copyright 2023, Cisco"
__email__ = "anersess@cisco.com"
__version__ = "v3"
__coauthor__ = "Saurabh Sharma"

import csv
import getpass
import os
from dnac import *

######################################
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
######################################


if __name__ == "__main__":
    env = {}
    # get Auth token and save in environment variable
    env["base_url"] = "https://10.8.6.56"  #input("DNAC URL eg https://dnac.example.com:  ")
    env["username"] = "admin" #"input("Username: ")
    env["password"] = getpass.getpass("DNAC Passowrd: ")
    env['token'] = get_auth_token(env)

    group_size = 99  # group size must be below 100.
    tags = get_device_tags(env)
    tagDict = {}
    taglist = []
    count = 0
    countTags = 0
    dnacDevs = []
    deploy = []  # To temporarily store deployment ID(s)
    date = time.strftime('%m-%d-%Y')  # USA Date Format


    print(f"{bcolors.OKGREEN}List of all TAGS available to deploy on{bcolors.ENDC}")
    for i in range(len(tags)):
        tagDict[tags[i]['name']] = tags[i]['id']
    for key in tagDict:
        taglist.append(key)
        print(f'{countTags} - {key}')
        countTags += 1

    while True:

        try:
            selectTag = int(input(f"{bcolors.OKGREEN}Select a tag number 0 to {countTags - 1}:  {bcolors.ENDC}"))
            yeorne = input(f"{bcolors.WARNING}Are you sure? y/n {taglist[selectTag]} {bcolors.ENDC}:  ")
            if yeorne == 'y':
                dnacDevs = get_devices_by_tag(env, tagDict[taglist[selectTag]])
                break

        except:
            print(f"{bcolors.WARNING}Try Again{bcolors.ENDC}")


    print()
    print()

    # Select project
    project = get_project_names(env) #  Get the project names from DNAC
    index = ''
    select_project = ''
    count_proj = 0
    projectList = []

    for proj in project:
        print(f'{count_proj} - {proj}')
        projectList.append(proj)
        count_proj += 1

    while True:
        try:
            index = int(input(f'{bcolors.OKGREEN}Please select a project 0 - {count_proj-1}:  {bcolors.ENDC}'))
            select_project = projectList[index]
            yeorne = input(f"{bcolors.WARNING}Are you sure? y/n {select_project}:  {bcolors.ENDC}")
            break
        except:
            print(f"{bcolors.FAIL}\nNot a valid Project name!\n {bcolors.ENDC}")


    print()
    print()

    # Select Project
    x = 0
    if select_project != '':
        template = get_template_id(env, select_project)  # Get template ID

        for i in range(0, len(template), 2):
            print(x, template[i], "Template ID:", template[i + 1])
            x += 1

    print()

    while select_project != 'q':

        print()
        try:
            selection = int(input(f"{bcolors.OKGREEN}Please Select a template to deploy 0-{x - 1}:  {bcolors.ENDC}"))
            convertSelection = selection + selection + 1  # Convert to proper index in list to pull correct ID
            yeorne = input(
                f"Are you sure you want to deploy {bcolors.WARNING}{template[convertSelection - 1]}{bcolors.ENDC}? y or n, -1 to quit:  ")

            if yeorne == "y":

                groups = [dnacDevs[x:x + group_size] for x in
                          range(0, len(dnacDevs),
                                group_size)]  # Pythonic way (list slicing) to break down list to groups of X devices

                for i in range(len(groups)):
                    #print(groups[i])
                    deploy.append([deploy_template(env, template[convertSelection],
                                                   groups[i])])  # Template ID is the second parameter

                if deploy: #Check for empty list
                    try:
                        with open('jobid.id', 'r') as read:
                            jobId = int(read.readline())

                    except FileNotFoundError: # Creates jobid file and initializes it and creates deployids directory
                        os.mkdir('./deployids')
                        with open('jobid.id', 'w') as f:
                            f.write("1000")
                        with open('jobid.id', 'r') as read:
                            jobId = int(read.readline())

                    with open('jobid.id', 'w') as f:
                        jobId = jobId + 1
                        strId = str(jobId)
                        f.write(strId)
                    print()
                    print("Deploy ID file: ", f'deploy_ids_{date}_job_{bcolors.WARNING}{strId}{bcolors.ENDC}.csv')

                ids = f'./deployids/deploy_ids_{date}_job_{strId}.csv'  # CSV to store deploy IDs
                # Write Deployment ID(s) to file
                with open(ids, 'a', newline='') as csvfile:
                    # creating a csv writer object
                    csvwriter = csv.writer(csvfile)
                    # writing the data rows
                    csvwriter.writerows(deploy)

                # print(template[convertSelection])
                break
            elif yeorne == 'q':
                break
            else:
                continue
        except IndexError:  # Catch a choice outside the list index
            print("BAD CHOICE!")
        except ValueError:  # Catch a non valid choice such as string entered
            print("BAD CHOICE!")
