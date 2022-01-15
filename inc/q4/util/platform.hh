#pragma once

// Platform detection:
// FROM: https://stackoverflow.com/questions/5919996/how-to-detect-reliably-mac-os-x-ios-linux-windows-in-c-preprocessor
#if defined(WIN32) || defined(_WIN32) || defined(__WIN32__) || defined(__NT__)
    #define Q4_HOST_PLATFORM_WINDOWS
    // #ifdef _WIN64
    //     // define something for Windows (64-bit only)
    // #else
    //     // define something for Windows (32-bit only)
    // #endif
#elif __APPLE__
    // #include <TargetConditionals.h>
    // #if TARGET_IPHONE_SIMULATOR
    //      // iOS, tvOS, or watchOS Simulator
    // #if TARGET_OS_MACCATALYST
    //      // Mac's Catalyst (ports iOS API into Mac, like UIKit).
    // #elif TARGET_OS_IPHONE
    //     // iOS, tvOS, or watchOS device
    // #elif TARGET_OS_MAC
    //     // Other kinds of Apple platforms
    // #else
    // #   error "Unknown Apple platform"
    // #endif
    #define Q4_HOST_PLATFORM_MACOS
#elif __linux__
    // linux
    #define Q4_HOST_PLATFORM_LINUX
#elif __unix__ // all unices not caught above
    // Unix
    #define Q4_HOST_PLATFORM_UNIX
#elif defined(_POSIX_VERSION)
    // POSIX
    #define Q4_HOST_PLATFORM_POSIX
#else
#   error "Unknown compiler/platform"
#endif
