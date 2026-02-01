#!/bin/bash
# This resets a connected pluto, loads firmware into ram, and boots it
#

#default IP address
ipaddr=192.168.2.1
password=analog

echo "Checking if build/pluto.dfu exists"
if [ ! -f ./build/pluto.dfu ] ; then
    echo "No file to upload"
    exit 1
fi
echo "dfu file found"

echo "Rebooting device into dfu/ram mode"
ssh_cmd()
{
    sshpass -p analog ssh -oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null -oCheckHostIP=no root@192.168.2.1 "$@"
    if [ "$?" -ne "0" ] ; then
        echo "ssh command '$1' failed"
        exit 1
    fi
}
ssh_cmd "device_reboot ram"
echo "Successfully rebooted device into ram mode"

echo "Awaiting Pluto DFU mode"
lines=0
attempt=0
while [ "${lines}" -le "8" -a "${attempt}" -le "10" ] 
do
    lines=$(sudo dfu-util -l -d 0456:b673,0456:b674 | wc -l)
    if [ "${lines}" -le "8" ] ; then
	sleep 1
    fi
    ((attempt++))
done
echo "Pluto rebooted into DFU mode successfully"

# -R resets/terminates the dfu after we are done
echo "Uploading firmware into RAM"
sudo dfu-util -R -d 0456:b673,0456:b674 -D ./build/pluto.dfu -a firmware.dfu
echo "Successfully uploaded firmware"
