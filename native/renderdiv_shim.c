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
        value[0] = '2';
        value[1] = '\0';
        return 1;
    }
    return __system_property_get(name, value);
}
