#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/of.h>
#include <linux/of_address.h>
#include <linux/io.h>
#include <linux/delay.h>        /* Add this for udelay */
#include <linux/miscdevice.h>
#include <linux/fs.h>
#include <linux/uaccess.h>

/* Register offsets */
#define AES_NAME0       0x00
#define AES_NAME1       0x04
#define AES_VERSION     0x08
#define AES_CTRL        0x20
#define AES_STATUS      0x24
#define AES_CONFIG      0x28
#define AES_KEY0        0x40
#define AES_BLOCK0      0x80
#define AES_RESULT0     0xC0

/* Control bits */
#define AES_CTRL_INIT   BIT(0)
#define AES_CTRL_NEXT   BIT(1)

/* Status bits */
#define AES_STATUS_READY BIT(0)
#define AES_STATUS_VALID BIT(1)

/* Config bits */
#define AES_CONFIG_ENCDEC  BIT(0)  /* 1=encrypt, 0=decrypt */
#define AES_CONFIG_KEYLEN  BIT(1)  /* 1=256bit, 0=128bit */

struct aes_dev {
    void __iomem *base;
    struct device *dev;
    struct miscdevice miscdev;
};

static struct aes_dev *aes_global; /* For easy testing */

static inline u32 aes_read(struct aes_dev *aes, u32 offset)
{
    return ioread32(aes->base + offset);
}

static inline void aes_write(struct aes_dev *aes, u32 offset, u32 value)
{
    iowrite32(value, aes->base + offset);
}

static int aes_wait_ready(struct aes_dev *aes, unsigned int timeout_ms)
{
    unsigned int count = timeout_ms * 100;
    
    while (count--) {
        if (aes_read(aes, AES_STATUS) & AES_STATUS_READY)
            return 0;
        udelay(10);
    }
    
    return -ETIMEDOUT;
}

static int aes_wait_valid(struct aes_dev *aes, unsigned int timeout_ms)
{
    unsigned int count = timeout_ms * 100;
    
    while (count--) {
        if (aes_read(aes, AES_STATUS) & AES_STATUS_VALID)
            return 0;
        udelay(10);
    }
    
    return -ETIMEDOUT;
}

/* Simple test function - encrypt one block with 128-bit key */
static int aes_encrypt_block_128(struct aes_dev *aes, 
                                  const u32 *key,
                                  const u32 *block,
                                  u32 *result)
{
    int ret, i;
    
    /* Configure: 128-bit key, encrypt mode */
    aes_write(aes, AES_CONFIG, AES_CONFIG_ENCDEC);
    
    /* Load key */
    for (i = 0; i < 4; i++)
        aes_write(aes, AES_KEY0 + (i * 4), key[i]);
    
    /* Trigger INIT for key expansion */
    aes_write(aes, AES_CTRL, AES_CTRL_INIT);
    
    /* Wait for ready after key init */
    ret = aes_wait_ready(aes, 100);
    if (ret) {
        dev_err(aes->dev, "Timeout waiting for ready after key init\n");
        return ret;
    }
    
    /* Load block */
    for (i = 0; i < 4; i++)
        aes_write(aes, AES_BLOCK0 + (i * 4), block[i]);
    
    /* Trigger NEXT for encryption */
    aes_write(aes, AES_CTRL, AES_CTRL_NEXT);
    
    /* Wait for valid result */
    ret = aes_wait_valid(aes, 100);
    if (ret) {
        dev_err(aes->dev, "Timeout waiting for valid result\n");
        return ret;
    }
    
    /* Read result */
    for (i = 0; i < 4; i++)
        result[i] = aes_read(aes, AES_RESULT0 + (i * 4));
    
    return 0;
}

/* Sysfs test interface - writes test vectors to kernel log */
static ssize_t test_store(struct device *dev, struct device_attribute *attr,
                          const char *buf, size_t count)
{
    struct aes_dev *aes = dev_get_drvdata(dev);
    u32 key[4] = {0};      /* All zeros for simple test */
    u32 block[4] = {0};    /* All zeros */
    u32 result[4];
    int ret;
    
    ret = aes_encrypt_block_128(aes, key, block, result);
    if (ret) {
        dev_err(dev, "Encryption failed: %d\n", ret);
        return ret;
    }
    
    dev_info(dev, "AES Test: Key=[0,0,0,0], Block=[0,0,0,0]\n");
    dev_info(dev, "Result: %08x %08x %08x %08x\n", 
             result[0], result[1], result[2], result[3]);
    /* Expected for AES-128, all-zero key and plaintext:
     * 0x66e94bd4 0xef8a2c3b 0x884cfa59 0xca342b2e */
    
    return count;
}
static DEVICE_ATTR_WO(test);

static struct attribute *aes_attrs[] = {
    &dev_attr_test.attr,
    NULL,
};
ATTRIBUTE_GROUPS(aes);

static int aes_device_probe(struct platform_device *pdev)
{
    struct device *dev = &pdev->dev;
    struct aes_dev *aes;
    struct resource *res;
    u32 name0, name1, version;
    int ret;
    
    pr_info("AES Device: Probe called\n");
    
    aes = devm_kzalloc(dev, sizeof(*aes), GFP_KERNEL);
    if (!aes)
        return -ENOMEM;
    
    aes->dev = dev;
    platform_set_drvdata(pdev, aes);
    aes_global = aes;
    
    /* Map registers */
    res = platform_get_resource(pdev, IORESOURCE_MEM, 0);
    aes->base = devm_ioremap_resource(dev, res);
    if (IS_ERR(aes->base))
        return PTR_ERR(aes->base);
    
    /* Read core info */
    name0 = aes_read(aes, AES_NAME0);
    name1 = aes_read(aes, AES_NAME1);
    version = aes_read(aes, AES_VERSION);
    
    dev_info(dev, "AES core found: name=0x%08x%08x version=0x%08x\n",
             name0, name1, version);
    
    /* Create sysfs attributes */
    ret = sysfs_create_groups(&dev->kobj, aes_groups);
    if (ret) {
        dev_err(dev, "Failed to create sysfs groups\n");
        return ret;
    }
    
    dev_info(dev, "AES driver loaded. Test with: echo 1 > /sys/devices/soc0/fpga-axi@0/80000000.aes/test\n");
    
    return 0;
}

static int aes_device_remove(struct platform_device *pdev)
{
    struct aes_dev *aes = platform_get_drvdata(pdev);
    
    sysfs_remove_groups(&pdev->dev.kobj, aes_groups);
    aes_global = NULL;
    
    pr_info("AES Device: Remove called\n");
    return 0;
}

static const struct of_device_id aes_device_of_match[] = {
    { .compatible = "secworks,aes-1.00", },
    { }
};
MODULE_DEVICE_TABLE(of, aes_device_of_match);

static struct platform_driver aes_device_driver = {
    .probe = aes_device_probe,
    .remove = aes_device_remove,
    .driver = {
        .name = "aes-secworks",
        .of_match_table = aes_device_of_match,
    },
};

module_platform_driver(aes_device_driver);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Morten");
MODULE_DESCRIPTION("Device driver for the Secworks AES accelerator");
