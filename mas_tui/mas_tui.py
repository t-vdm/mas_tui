from __future__ import print_function, unicode_literals

import concurrent.futures
import json
import os
import subprocess

from PyInquirer import print_json, prompt
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich import print

console = Console()

# checks if Intel MAS is installed, and displays version.
def get_mas_info():
    try:
        masversion = subprocess.run('intelmas version -output json', capture_output=True,shell=True)
        json_mas_version = masversion.stdout
        mas_version = json.loads(json_mas_version)
    except:
        print('Could not fetch Intel MAS version.')
        print('[bold red]Possible reasons:[/bold red]')
        print('1. Are you sure Intel MAS is installed on this PC?')
        print('2. Did you run the program as Administrator?')
        exit() 
    return mas_version
# gets Basic SSD info from Intel MAS
def get_ssd_info():    
    print('Requesting SSD INFO...')
    ssdinfo = subprocess.run('intelmas show -output json -intelssd', capture_output=True,shell=True)
    print('Requesting SSD INFO...[DONE]')
    return ssdinfo
# gets sensor health info from Intel MAs
def get_sensor_info():    
    print('Requesting SENSOR INFO...')
    sensorinfo = subprocess.run('intelmas show -output json -sensor -intelssd', capture_output=True,shell=True)
    print('Requesting SENSOR INFO..[DONE]')
    return sensorinfo
# request the namespace info
def get_namespace_info():
    print('Requesting NAMESPACE INFO...')
    namespaceinfo = subprocess.run('intelmas show -o json -intelssd -identify -namespace attached', capture_output=True,shell=True)
    print('Requesting NAMESPACE INFO..[DONE]')
    return namespaceinfo    
# request namespace info of a specific drive
def namespace_check(serial):
    namespaceinfo = subprocess.run(f'intelmas show -o json -intelssd {serial} -identify -namespace attached', capture_output=True,shell=True)
    json_namespace_info = namespaceinfo.stdout
    namespace_info = json.loads(json_namespace_info)
    try:
        namespace = namespace_info[next(iter(namespace_info))]['Namespace ID']
        namespace = len(namespace_info[next(iter(namespace_info))])
        namespace = namespace_info[list(namespace_info)[-1]]
        namespace = namespace.get('Namespace ID')
        return namespace

    except:
        if bool(namespace_info[next(iter(namespace_info))]) == False:
            namespace = 0
            return namespace
        if namespace_info[next(iter(namespace_info))]['Status'] == 'The selected drive does not support this feature.':
            namespace = 'N/A'
            return namespace
        elif namespace_info[next(iter(namespace_info))]['Status'] == 'Device does not support this command set.':
            namespace = 'N/A'
            return namespace
        else:
            pass
# deletes all namespaces attached to a specific drive            
def delete_namespaces(serial):
    ns_amount = namespace_check(serial)
    if ns_amount == 'N/A':
        print('NO NAMESPACES AVAILABLE TO DELETE')
    else:
        for x in range(ns_amount):
            x= x+1
            subprocess.run(f'intelmas detach -f -intelssd {serial} -namespace {x}', capture_output=True,shell=True)
            subprocess.run(f'intelmas delete -f -intelssd {serial} -namespace {x}', capture_output=True,shell=True)
            subprocess.run(f'intelmas reset -f -intelssd {serial} -nvmecontroller', capture_output=True,shell=True)
            print(f'Namespace {x} on drive index {serial} deleted...')
# restores 1 namespace and attaches it to a specific drive, size of ns=maxLBA
def reset_namespaces(serial):
    #delete_namespaces(serial)
    maxlba_info = subprocess.run(f'intelmas  show -o json -d NativeMaxLBA -intelssd {serial}', capture_output=True,shell=True)
    maxlba_info = maxlba_info.stdout
    maxlba_info = json.loads(maxlba_info)
    drive = list(maxlba_info.keys())[0]
    maxlba = maxlba_info[drive]['NativeMaxLBA']
    maxlba = int(maxlba)+1
    print(f'Got Native MaxLBA of the drive = {maxlba}')
    subprocess.run(f'intelmas create -namespace -intelssd {serial} size={maxlba}', capture_output=True,shell=True)
    print(f'Created Namespace on {serial} with size {maxlba}')
    subprocess.run(f'intelmas attach -intelssd {serial} -namespace 1 -nvmecontroller 0', capture_output=True,shell=True)
    subprocess.run(f'intelmas reset -f -intelssd {serial} -nvmecontroller', capture_output=True,shell=True)
    print(f'Attached Namespace on {serial} with size {maxlba}')
# helper to color the health in the table
def health_check(health):
    if health == 'Healthy':
        health_style = f"[bold green]{health}[/bold green]"
    else:
        health_style = f"[bold red]{health}[/bold red]"
    return health_style

# helper to verify wear of the drive
def wear_check(used):
    if used == 'Property not found':
        used = f"[bold red]N/A[/bold red]"
    else:
        used = str(f'{used}%')
    return used

# helper to verify wear of the drive
def temp_check(temp):
    if temp == 'Property not found':
        temp = f"[bold red]N/A[/bold red]"
    else:
        temp = str(temp)
        temp = temp[:-8]
    return temp


# helper to color fw in the table
def firmware_check(fw_upd):
    if fw_upd == 'The selected drive contains current firmware as of this tool release.':
        fw_upd = f"[bold green]Up to date.[/bold green]"
    elif fw_upd == 'Please contact Intel Customer Support for further assistance at the following website: http://www.intel.com/go/ssdsupport.':
        fw_upd = f"[bold red]Contact Support.[/bold red]"
    else:
        fw_upd = f"[bold yellow]{fw_upd}[/bold yellow]"
    return fw_upd
# function to update firmware on either a specific drive or all drives
def firmware_update(index):
    if index == 'all':
        for ssd in ssd_info:
            if ssd_info[ssd]['ProductFamily'] == 'ProductFamily not found':
                print('Non Intel drive found, skipping.')
            elif ssd_info[ssd]['ProductFamily'] == 'Property not found':
                print('Non Intel drive found, skipping.')
            else:
                ssd_serial = ssd_info[ssd]['SerialNumber']
                print(f'Updating firmware on: {ssd_serial}...')
                firmware_update = subprocess.run(f'intelmas load -f -output json -intelssd {ssd_serial}', capture_output=True,shell=True)
                firmware_update_result = firmware_update.stdout
                firmware_update_result  = json.loads(firmware_update_result)
                firmware_update_result = firmware_update_result[ssd]['Status']
                print(f'{firmware_update_result}')
                #return firmware_update_result
    
    else:
        print(f'Updating firmware on index: {index}...')
        firmware_update = subprocess.run(f'intelmas load -f -output json -intelssd {index}', capture_output=True,shell=True)
        firmware_update_result = firmware_update.stdout
        firmware_update_result  = json.loads(firmware_update_result)
        for result in firmware_update_result:
            drive = result
            firmware_update_result = firmware_update_result[result]['Status']
            print(f'{drive} : {firmware_update_result}')
        return firmware_update_result
    print('Updated all drives')
# function to erase or secure erase all drives or selected drive, depending on NVMe format available or not
def secure_erase(index):
    if index == 'all':
        for ssd in ssd_info:
            if ssd_info[ssd]['ProductFamily'] == 'ProductFamily not found':
                print('Non Intel drive found, skipping.')
            elif ssd_info[ssd]['ProductFamily'] == 'Property not found':
                print('Non Intel drive found, skipping.')
            else:
                ssd_serial = ssd_info[ssd]['SerialNumber']
                print(f'Secure erasing: {ssd_serial}...')
                secure_erase = subprocess.run(f'intelmas delete -f -output json -intelssd {ssd_serial}', capture_output=True,shell=True)
                secure_erase_result = secure_erase.stdout
                secure_erase_result = secure_erase_result.decode()
                secure_erase_result = secure_erase_result.replace("/", '?')
                secure_erase_result = json.loads(secure_erase_result)
                secure_erase_result = secure_erase_result[ssd]['Status']
                print(f'{secure_erase_result}')  
    else:
        print(f'Secure erasing:: {index}...')
        secure_erase = subprocess.run(f'intelmas delete -f -output json -intelssd {index}', capture_output=True,shell=True)
        secure_erase_result = secure_erase.stdout
        secure_erase_result = secure_erase_result.decode()
        secure_erase_result = secure_erase_result.replace("/", '?')
        secure_erase_result = json.loads(secure_erase_result)
        for result in secure_erase_result:
            drive = result
            secure_erase_result = secure_erase_result[result]['Status']
            print(f'{drive} : {secure_erase_result}')
        return secure_erase_result
    print('Secure-Erased all drives')
# creates the table 
def setup_table():
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=2)
    table.add_column("SSD")
    table.add_column("SERIAL")
    table.add_column("HEALTH")
    table.add_column("WEAR",width=4)
    table.add_column("TEMP")
    table.add_column("# NS",width=4)
    table.add_column("FW")
    table.add_column("FW UPDATE?")
    return table
# generate rows for the table
def generate_table_rows(table):
    if len(ssd_info) == 1:
        for ssd in ssd_info:
            if ssd_info[ssd]['ProductFamily'] == 'ProductFamily not found':
                print('Non Intel drive found, skipping.')
            elif ssd_info[ssd]['ProductFamily'] == 'Property not found':
                print('Non Intel drive found, skipping.')
            else:
                index = ssd_info[ssd]['Index']
                ssd_name = ssd_info[ssd]['ProductFamily']
                ssd_serial = ssd_info[ssd]['SerialNumber']
                health = ssd_info[ssd]['DeviceStatus']
                used = sensor_info['PercentageUsed']
                temp = sensor_info['Temperature']
                fw = ssd_info[ssd]['Firmware']
                fw_upd = ssd_info[ssd]['FirmwareUpdateAvailable']
                namespace = namespace_check(str(ssd_serial))
                table.add_row(
                    str(index),
                    str(ssd_name),
                    str(ssd_serial),
                    health_check(health),
                    wear_check(used),
                    temp_check(temp),
                    str(namespace),
                    fw,
                    firmware_check(fw_upd)
                )
                index_list.append(str(index))
                index_list_alt.append(str(index))
    else:
        for ssd in ssd_info:
            if ssd_info[ssd]['ProductFamily'] == 'ProductFamily not found':
                print('Non Intel drive found, skipping.')
            elif ssd_info[ssd]['ProductFamily'] == 'Property not found':
                print('Non Intel drive found, skipping.')
            else:
                index = ssd_info[ssd]['Index']
                ssd_name = ssd_info[ssd]['ProductFamily']
                ssd_serial = ssd_info[ssd]['SerialNumber']
                health = ssd_info[ssd]['DeviceStatus']
                used = sensor_info[ssd]['PercentageUsed']
                temp = sensor_info[ssd]['Temperature']
                fw = ssd_info[ssd]['Firmware']
                fw_upd = ssd_info[ssd]['FirmwareUpdateAvailable']
                namespace = namespace_check(str(ssd_serial))
                table.add_row(
                    str(index),
                    str(ssd_name),
                    str(ssd_serial),
                    health_check(health),
                    wear_check(used),
                    temp_check(temp),
                    str(namespace),
                    fw,
                    firmware_check(fw_upd)
                )
                index_list.append(str(index))
                index_list_alt.append(str(index))
# refreshes the drive info.
def refresh():
    index_list.clear()
    index_list.append('all')
    index_list.append('back')
    index_list_alt.clear()
    index_list_alt.append('back')
    with concurrent.futures.ThreadPoolExecutor() as executor:
        f1 = executor.submit(get_ssd_info)
        f2 = executor.submit(get_sensor_info)
        ssdinfo = f1.result()
        sensorinfo = f2.result()
    json_ssd_out = ssdinfo.stdout
    json_sensorinfo = sensorinfo.stdout
    ssd_info = json.loads(json_ssd_out)    
    sensor_info = json.loads(json_sensorinfo)    
    table = setup_table()
    generate_table_rows(table)
    os.system('cls' if os.name == 'nt' else 'clear') 
    console.print(table)
    return ssd_info, sensor_info


mas_version = get_mas_info()

with concurrent.futures.ThreadPoolExecutor() as executor:
    f1 = executor.submit(get_ssd_info)
    f2 = executor.submit(get_sensor_info)
    f3 = executor.submit(get_namespace_info)
    ssdinfo = f1.result()
    sensorinfo = f2.result()
    namespaceinfo = f3.result()

# convert collected MAS info to JSON objects    
json_ssd_out = ssdinfo.stdout
json_sensorinfo = sensorinfo.stdout
json_namespace_info = namespaceinfo.stdout

namespace_info = json.loads(json_namespace_info)
ssd_info = json.loads(json_ssd_out)    
sensor_info = json.loads(json_sensorinfo)
 
#clear screen
os.system('cls' if os.name == 'nt' else 'clear')
# SCRIPT
print(mas_version['Version Information']['Name'])
print(mas_version['Version Information']['Version'])

# list for user input options
index_list = ['all','back']
index_list_alt = ['back']
questions = [
    {
        'type': 'list',
        'name': 'action',
        'message': 'What do you want to do?',
        'choices': [
            '1.FW UPDATE AND SECURE ERASE',
            '2.SECURE ERASE ONLY',
            '3.FW UPDATE ONLY',
            '4.DELETE NAMESPACES',
            '5.RESTORE NAMESPACES',
            '9.REFRESH DRIVE INFO',
            '0.EXIT'
        ]
    }
]


# Set up table for display
table = setup_table()
generate_table_rows(table)

# show the table
console.print(table)
while True:
    answers = prompt(questions)
    if answers['action'] == '1.FW UPDATE AND SECURE ERASE':
        drive_select = Prompt.ask("Select drive to update + wipe", choices=index_list,default='all')
        if drive_select == 'back':
            refresh()
        else:
            secure_erase(drive_select)
            firmware_update(drive_select)
    elif answers['action'] == '2.SECURE ERASE ONLY':
        drive_select = Prompt.ask("Select drive to wipe", choices=index_list,default='all')
        if drive_select == 'back':
            refresh()
        else:
            secure_erase(drive_select)
    elif answers['action'] == '3.FW UPDATE ONLY':
        drive_select = Prompt.ask("Select drive to update", choices=index_list,default='all')#
        if drive_select == 'back':
            refresh()
        else:
            firmware_update(drive_select)
    elif answers['action'] == '4.DELETE NAMESPACES':
        drive_select = Prompt.ask("Select drive to delete namespaces", choices=index_list_alt,default='back')
        if drive_select == 'back':
            refresh()
        else:
            delete_namespaces(drive_select)
    elif answers['action'] == '5.RESTORE NAMESPACES':
        drive_select = Prompt.ask("Select drive to reset namespaces", choices=index_list_alt,default='back')
        if drive_select == 'back':
            refresh()
        else:
            delete_namespaces(drive_select)
            reset_namespaces(drive_select)
    elif answers['action'] == '9.REFRESH DRIVE INFO':
        index_list.clear()
        index_list.append('all')
        index_list.append('back')
        index_list_alt.clear()
        index_list_alt.append('back')
        with concurrent.futures.ThreadPoolExecutor() as executor:
            f1 = executor.submit(get_ssd_info)
            f2 = executor.submit(get_sensor_info)
            ssdinfo = f1.result()
            sensorinfo = f2.result()
        json_ssd_out = ssdinfo.stdout
        json_sensorinfo = sensorinfo.stdout
        ssd_info = json.loads(json_ssd_out)    
        sensor_info = json.loads(json_sensorinfo)    
        table = setup_table()
        generate_table_rows(table)
        os.system('cls' if os.name == 'nt' else 'clear') 
        console.print(table)
    elif answers['action'] == '0.EXIT':
        print(f'EXITING PROGRAM..')
        break
    else:
        print('NO VALID ACTION WAS PROVIDED.')
print('Thank you for using Intel MAS TUI.')

