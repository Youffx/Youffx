# AnyKernel3 Ramdisk Mod Script
# osm0sis @ xda-developers

## AnyKernel setup
# begin properties
properties() { '
kernel.string=LandVe - Rosemary
do.devicecheck=1
do.modules=0
do.systemless=1
do.cleanup=1
do.cleanuponabort=1
device.name1=rosemary
device.name2=secret
device.name3=maltose
supported.versions=12-16
'; } # end properties

## AnyKernel file attributes
# set permissions / ownership for included ramdisk files
boot_attributes() {
	set_perm_recursive 0 0 755 644 "$ramdisk/*";
	set_perm_recursive 0 0 750 750 "$ramdisk/init*" "$ramdisk/sbin";
}

# shell variables
block="/dev/block/bootdevice/by-name/boot";
is_slot_device=1;
ramdisk_compression=auto;
patch_vbmeta_flag=auto;

## AnyKernel methods (DO NOT CHANGE)
# import patching functions/variables - see for reference
. tools/ak3-core.sh;

# Apply Image & dtbo
mv kernels/Image.gz-dtb Image.gz-dtb;

## AnyKernel install
dump_boot;
write_boot;
