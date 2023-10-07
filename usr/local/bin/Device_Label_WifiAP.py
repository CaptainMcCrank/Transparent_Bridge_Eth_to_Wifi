#!/usr/bin/env python3
import pdb
import os
import socket
import netifaces as ni
from PIL import Image, ImageFont, ImageDraw
from font_fredoka_one import FredokaOne
from inky import InkyWHAT
import math
import subprocess

inky_display = InkyWHAT("red")
inky_display.set_border(inky_display.WHITE)


# I want to be able to poll relevant networking data.
# If a nic is not attached, it won't sow up in the /sys/class/net/ directory.  
# this means I can write a loop that polls the directory for all identified/connected interfaces.
# The loopback address on lo will represent a state of "unknown" 
# if a nic is available, but disabled, it will show up as "down".  
# This can happen when wlan0 is there but not configured & tuned to connect to a wifi network. 

# build a list of network interfaces

network_list = []
interface_list = os.listdir('/sys/class/net/')


def getDeviceData(value):
    inputFile = "/boot/device.ver"
    with open(inputFile, 'r') as filedata:
        for line in filedata:
            if value in line:
                return line
        return value + " NOT FOUND"


def is_interface_up(interface):
    #function returns true if the interface is up.
    addr = ni.ifaddresses(interface)
    return ni.AF_INET in addr


def get_interface_info2():
    for iface in ni.interfaces():
        if iface == 'lo' or iface.startswith('vbox'):
            continue
        iface_details = ni.ifaddresses(iface)
        if ni.AF_INET in iface_details:
            message = iface + ' has address: ' + iface_details[ni.AF_INET][0]['addr']
            print(message)

def get_attached_devices():
    # sudo iw dev wlan0 station dump | grep Station | wc -l

    # I need to run two commands- and note that they both have share the first two commands being piped together
    # Unfortunately I can't reuse the process, so I'll have to reconstruct it and call it twice.
    # sudo iw dev wlan0 station dump | grep Station | wc -l
    # sudo iw dev wlan0 station dump | grep Station | awk '{ print $2 }'
    # So I define the first two commands being piped together:

    
    iwProc = subprocess.Popen(["iw", "dev", "wlan0", "station", "dump"], stdout=subprocess.PIPE, text=True)
    grepProc = subprocess.Popen(["grep", "Station"], stdin=iwProc.stdout, stdout=subprocess.PIPE, text=True)

    # And now I go after the count of devices attached.  Note that I'm accepting grepProc as stdin:
    wcProc = subprocess.Popen(["wc", "-l"], stdin=grepProc.stdout, stdout=subprocess.PIPE, text=True)
    DeviceCount, error = wcProc.communicate()

    # I lost my procs because I called the communicate method, so I need to rebuild them:
    iwProc = subprocess.Popen(["iw", "dev", "wlan0", "station", "dump"], stdout=subprocess.PIPE, text=True)
    grepProc = subprocess.Popen(["grep", "Station"], stdin=iwProc.stdout, stdout=subprocess.PIPE, text=True)
    
    # And here I go for the mac addresses that are attached.  Note that I'm accepting grepProc as stdin:
    awkProc = subprocess.Popen(["awk", "{ print $2 }"], stdin=grepProc.stdout, stdout=subprocess.PIPE, text=True)
    MacAddresses, error = awkProc.communicate()
    return DeviceCount.strip() + " devices attached.", MacAddresses.splitlines()


def get_interface_info(interface_list):
    #for every interface on the OS, we're going to gather data about it's state and current ip address.
    
    print(str(len(interface_list)) + " interfaces discovered")
    for interface in interface_list:
        state=open('/sys/class/net/' + str(interface) + '/operstate').readlines() # use open method to check the file.  Readlines pulls array- get first line with an [0] index.
        #if an interface is offline, we need to manually specify an unassigned ip address. 
        if (state[0] != "down\n"):
            # Ok- i'm in a hack here.
            # The transparent firewall is showing a dupeplicate dhcp address on the 
            # eth0 interface.  Might be due to implementaiton of proxy.
            # I need to check for this condition by sering if there are more
            # than 2 addresses presented in the following line:

            if (interface=='eth0'):
                
                if (len(ni.ifaddresses(interface)[ni.AF_INET])>1):

                #If we're here, we found more than one ip address.  Let's only save if the value is not 10.0.0.1 # HACK HACK HACK HACK HACK
                    print( ni.ifaddresses(interface)[ni.AF_INET][0]['addr']) 
                    if("10.0.0.1" != ni.ifaddresses(interface)[ni.AF_INET][0]['addr']): 
                        iface_ip_address = ni.ifaddresses(interface)[ni.AF_INET][0]['addr']
                    else:
                        iface_ip_address = ni.ifaddresses(interface)[ni.AF_INET][1]['addr']
            else:

                if (state[0]== "down\n"):
                    iface_ip_address="unassigned"
                else:
                    iface_ip_address = ni.ifaddresses(interface)[ni.AF_INET][0]['addr']
        else:
            iface_ip_address = "unassigned"
        

        #we'll only add lo data if there is 3 or fewer interfaces
        if (len(interface_list) > 3):
            if (interface != "lo"):
                print("We're adding a " + interface + " device to the network list")
                network_list.append({'iface_name':interface, 'address':iface_ip_address, 'state':state })

        if (len(interface_list) <= 3):
                network_list.append({'iface_name':interface, 'address':iface_ip_address, 'state':state })
    
    return network_list


def main():
    img = Image.new("P", (inky_display.WIDTH, inky_display.HEIGHT))
    draw = ImageDraw.Draw(img)
    import textwrap

    message = "" 
    #for item in get_interface_info(interface_list):

    for iface in ni.interfaces():
        if iface == 'lo' or iface.startswith('vbox'):
            continue
        iface_details = ni.ifaddresses(iface)
        if ni.AF_INET in iface_details:
            message += iface + ' has address: ' + iface_details[ni.AF_INET][0]['addr']
            
    
    wrappedText = textwrap.wrap(message, width=36)


    #JoinedText= "\n".join(wrappedText)

    BuildDate = getDeviceData("BuildDate:")
    BuildDescription = getDeviceData("Description")
    BuildAuthor = getDeviceData("Author")
    BuildVer = getDeviceData("Ver")
    BuildDescription = textwrap.wrap(BuildDescription, width=36)
    JoinedText= "\n".join(BuildDescription)

    WifiClients=get_attached_devices()

    print(BuildDescription)

    font = ImageFont.truetype(FredokaOne, 18)
    w,h = font.getsize(message)
    x = (inky_display.WIDTH/ 8) 
    y = (inky_display.HEIGHT / 2) - (w/2)
    #draw.text((x, y), JoinedText, inky_display.RED, font)
    messageRowCount = print(math.ceil(len(message)/36))

    draw.text((0, 5), socket.getfqdn() + ".local", inky_display.RED, font)

    ifaceStart = 30 # We will use to space text appropriately

    draw.text((x, ifaceStart), message, inky_display.RED, font)

    draw.text((x, ifaceStart * 2.1), BuildDate, inky_display.RED, font)

#    draw.text((x, ifaceStart * 3.1), BuildAuthor, inky_display.RED, font)

#    draw.text((x, ifaceStart * 4.1), BuildVer, inky_display.RED, font)

#    draw.text((0, ifaceStart * 3.1), JoinedText, inky_display.BLACK, font)

    draw.text((0, ifaceStart * 3.1), WifiClients[0], inky_display.BLACK, font)

    row = 4.1 # an index for the starting point of our Y coordinate for the text.  will be offset with the ifacestart value.
    counter = 0 # an index for the element we're on in the array.
    
    # We're going to print the mac address of every attached device up to 14 clients.
    for macaddress in WifiClients[1]:
        if (counter % 2 == 0):
            #if the index is even, we'll print it on the left side.
            draw.text((0, ifaceStart * row), macaddress, inky_display.BLACK, font)
        else:
            #if the index is odd, we'll print it on the right side and increment our counter. 
            draw.text((160, ifaceStart * row), macaddress, inky_display.BLACK, font)
            row += 1    
        counter += 1
        if counter == 13:
            break

    inky_display.set_image(img)
    inky_display.show()


if __name__ == "__main__":
    main()




