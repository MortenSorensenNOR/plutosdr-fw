ifneq ($(KERNELRELEASE),)
    obj-m := aes_driver.o
    ccflags-y := -fno-stack-protector

else
    KDIR ?= $(PWD)/../linux
    ARCH ?= arm
    CROSS_COMPILE ?= arm-linux-gnueabihf-
    
all:
	$(MAKE) -C $(KDIR) M=$(PWD) ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) \
		CONFIG_GCC_PLUGINS=n CONFIG_CC_STACKPROTECTOR=n CONFIG_STACKPROTECTOR=n modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) clean

help:
	@echo "Build kernel module for PlutoSDR"
	@echo "  make          - build the module"
	@echo "  make clean    - clean build files"
	@echo ""
	@echo "Variables:"
	@echo "  KDIR=$(KDIR)"
	@echo "  ARCH=$(ARCH)"
	@echo "  CROSS_COMPILE=$(CROSS_COMPILE)"

.PHONY: all clean help

endif
