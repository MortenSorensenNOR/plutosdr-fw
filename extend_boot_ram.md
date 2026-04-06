ssh root@192.168.2.1 "fw_setenv dfu_alt_info 'dummy.dfu ram 0 0;firmware.dfu ram 0x2080000 0x3000000' && fw_setenv dfu_ram_info 'echo ok'"
