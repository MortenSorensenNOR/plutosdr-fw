# IMPORTANT NOTICE:  
In order to get the new firmware with python + packages to flash nicely into ram, the size of the ramdisk has to be increased.   
It's therefore required to run this (with the Pluto plugged in) to increase it:  
```  
ssh root@192.168.2.1 "fw_setenv dfu_alt_info 'dummy.dfu ram 0 0;firmware.dfu ram 0x2080000 0x3000000' && fw_setenv dfu_ram_info 'echo ok'"  
```  
Replace 192.168.2.1 if you have multiple radios and have configured them to have different local addresses.  
