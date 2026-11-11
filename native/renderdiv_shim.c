/* SPDX-License-Identifier: GPL-2.0-or-later */
/*
 * App-local override for Blender's own render scale system property.
 * Does not write Android system properties and does not affect other apps.
 * The original Blender native code already scales input and coordinates.
 */
#include <sys/system_properties.h>
#include <string.h>

__attribute__((visibility("default")))
int blender_renderdiv_get(const char *name, char *value)
{
    if (name != 0 && value != 0 &&
        strcmp(name, "debug.blender.renderdiv") == 0) {
        value[0] = '2';
        value[1] = '\0';
        return 1;
    }
    return __system_property_get(name, value);
}
