/* SPDX-License-Identifier: GPL-2.0-or-later */
/*
 * Limit the Blender Android alpha-4 main loop's zero-timeout busy polling,
 * while retaining its native event wakeups and WM conditional redraw.
 * Applied only to the libblender.so dynamic symbol import, not system-wide.
 */
#include <android/looper.h>
#include <stdint.h>
#include <string.h>
#include <sys/system_properties.h>
#include <time.h>

#ifndef MOBILE_RENDER_DIVISOR
#define MOBILE_RENDER_DIVISOR 2
#endif
#if MOBILE_RENDER_DIVISOR < 1 || MOBILE_RENDER_DIVISOR > 4
#error MOBILE_RENDER_DIVISOR must be 1, 2, 3, or 4
#endif

static _Thread_local uint64_t last_event_ms;

static uint64_t clock_ms(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t) != 0) {
        return 0;
    }
    return (uint64_t)t.tv_sec * 1000u + (uint64_t)t.tv_nsec / 1000000u;
}

__attribute__((visibility("default")))
int blender_pollOnce(int timeoutMillis, int *outFd, int *outEvents, void **outData)
{
    int effective = timeoutMillis;
    uint64_t now = 0;
    if (timeoutMillis == 0) {
        now = clock_ms();
        if (now != 0) {
            if (last_event_ms == 0 || now < last_event_ms) {
                last_event_ms = now;
            }
            /* Recent event: 10ms; idle >800ms: 24ms (~42 ticks/sec).
             * The Android looper wakes immediately for real incoming events.
             */
            effective = now - last_event_ms < 800 ? 10 : 24;
        }
    }
    int result = ALooper_pollOnce(effective, outFd, outEvents, outData);
    if (timeoutMillis == 0 && now != 0 &&
        (result >= 0 || result == ALOOPER_POLL_WAKE || result == ALOOPER_POLL_CALLBACK)) {
        last_event_ms = clock_ms();
    }
    return result;
}

__attribute__((visibility("default")))
int blender_renderdiv_get(const char *name, char *value)
{
    if (name != 0 && value != 0 && strcmp(name, "debug.blender.renderdiv") == 0) {
#if MOBILE_RENDER_DIVISOR == 1
        value[0] = '1';
#elif MOBILE_RENDER_DIVISOR == 2
        value[0] = '2';
#elif MOBILE_RENDER_DIVISOR == 3
        value[0] = '3';
#else
        value[0] = '4';
#endif
        value[1] = '\0';
        return 1;
    }
    /* Desktop Blender's layout is scaled as well as the framebuffer.
     * With 2x buffer reduction, upstream default 160 UI DPI appears too
     * large on a narrow landscape phone. The Android port explicitly
     * supports debug.blender.uidpi range 96..320; choose 96 for a compact
     * layout without changing the device-wide display density. */
    if (name != 0 && value != 0 &&
        strcmp(name, "debug.blender.uidpi") == 0) {
        value[0] = '9';
        value[1] = '6';
        value[2] = '\0';
        return 2;
    }
    /* Android Blender's own source uses this property to choose a
     * smaller swapchain on low-memory devices. Scope override to Blender. */
    if (name != 0 && value != 0 &&
        strcmp(name, "debug.blender.lowmem") == 0) {
        value[0] = '1';
        value[1] = '\0';
        return 1;
    }
    return __system_property_get(name, value);
}
