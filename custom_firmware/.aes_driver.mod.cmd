cmd_/build/custom_firmware/aes_driver.mod := printf '%s\n'   aes_driver.o | awk '!x[$$0]++ { print("/build/custom_firmware/"$$0) }' > /build/custom_firmware/aes_driver.mod
