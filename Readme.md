# FW_Transparent_Bridge_Eth_to_Wifi
by 🗿Patrick McCanna🗿

## Overview
This Recipe generates a wifi device that bridges an ethernet network and exposes it to a wifi network.  You can use this to turn your spare pi into wifi access points that expose an existing ethernet network.

## Prerequisites
* One Raspberry Pi 3 or greater
* One Class 10 SD card of 8gb or greater
* SDCard ripping software
    * https://www.raspberrypi.com/software/
* An sdcard writer (either integrated in laptop or availabile from [Amazon](https://www.amazon.com/Acuvar-Speed-Memory-Reader-Writer/dp/B00R07WNRY))

## Build Overview

login: pi
pwd: ChangeDefaultPWD3331333

This build bridges your ethernet network and exposes it via wifi.  This means a few things:
* Your existing dhcp solution can be extended to your wifi network.
* Your wifi network is not doing any bizarre double natting.  You're using the same ip range of your lan.  
*  Log into the system and run the command `arp -a | grep wlan0` to see the hostnames & Ip addresses of all devices attached to the wlan0 interface.  


It uses eth for internet access and the wifi interface vends network to anything attached.  

### Major Software Components

| Software | Description |
| ----------- | ----------- |
| [lighttpd](https://www.lighttpd.net/) | Webserver software (Not used in current build- but useful if you use web management software) |
| [avahi](https://www.avahi.org) | Avahi is a system which facilitates service discovery on a local network via the mDNS/DNS-SD protocol suite) |
| [hostapd](https://w1.fi/hostapd/) | a user space daemon for access point and authentication servers. It implements IEEE 802.11 access point management, IEEE 802.1X/WPA/WPA2/EAP Authenticators, RADIUS client, EAP server, and RADIUS authentication server) |
| [inkywhat](https://github.com/pimoroni/inky) | a 400x300 pixel electronic paper (ePaper / eInk / EPD) display for Raspberry Pi) |
| [bridge networking](https://www.raspberrypi.com/documentation/computers/configuration.html#setting-up-a-bridged-wireless-access-point) | The Raspberry Pi can be used as a bridged wireless access point within an existing Ethernet network. This will extend the network to wireless computers and devices.) |


## Setup instructions
* Follow instructions for building an image using ansible containers.

1. Install Docker 
2. Clone firmware development containers 
3. Tune your docker-compose file (to build the containers for use on your system)
4. Build & Launch Containers
5. Connect to our container and validate connectivity.
6. Clone the Transparent_Bridge_Eth_to_Wifi project into your DockerVolume directory on your host system.
7. build a recipient device using raspberry pi imager with a known credential and set it's hostname to ansibledest.local
9. attach to your ansible container
10. use ssh-copy-id command to copy a key from your ansible container to the target device
11. cd into /home/pi/Playbooks/Transparent_Bridge_Eth_to_Wifi
12. run the command ansible-playbook run.yml 


### Acquire hardware
The FW_Transparent_Bridge_Wifi_To_Eth depends on the following list of hardware:

| Quantity   | Device   |   
| :-------------| :-------------|
| 1 | [Raspberry Pi Mod 3 or Raspberry pi 4](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/) 
| 1 | [8 GB (or greater) Class 10 Ultra Micro SD](https://www.amazon.com/Sandisk-Ultra-Micro-UHS-I-Adapter/dp/B073K14CVB/ref=sr_1_sc_1?s=electronics&ie=UTF8&qid=1532625085&sr=1-1-spell&keywords=16+gb+micro+sdcard)|
| 1 | [ AWUS036ACH ](https://store.rokland.com/products/alfa-awus036ach-802-11ac-high-power-ac1200-dual-band-wifi-usb-adapter) |
| 1 | [Power Supply for Pi 3](https://www.amazon.com/Raspberry-Supply-Certified-Compatible-Adapter/dp/B075XMTQJC/ref=sr_1_5?s=electronics&ie=UTF8&qid=1532625410&sr=1-5&keywords=USB+charger+for+raspberry+pi) |


