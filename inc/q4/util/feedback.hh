#pragma once

#include <cstdarg>
#include <cstdio>
#include <cstdlib>

namespace q4 {

inline static size_t const FEEDBACK_BUFFER_SIZE_IN_BYTES = 1024;
inline static int const    PANIC_EXIT_CODE               = 42;

inline static void panic(char const* fmt, ...);
inline static void error(char const* fmt, ...);
inline static void warning(char const* fmt, ...);
inline static void info(char const* fmt, ...);
inline static void trace(char const* fmt, ...);


//
//
// Implementation:
//
//

static char message_buffer[FEEDBACK_BUFFER_SIZE_IN_BYTES];

inline static void __vreport(char const* prefix, char const* fmt, va_list ap) {
    // we can only use 'ap' once:
    {
        int buf_len_without_ellipses = FEEDBACK_BUFFER_SIZE_IN_BYTES-4;
        int wc = vsnprintf(message_buffer, buf_len_without_ellipses, fmt, ap);
        if (wc >= buf_len_without_ellipses) {
            sprintf(message_buffer + buf_len_without_ellipses, "...");
        }
    }
    
    fprintf(stderr, "%s:\t", prefix);
    for (char const* cp = message_buffer; *cp; cp++) {
        fputc(*cp, stderr);
        if (*cp == '\n') {
            fputc('\t', stderr);
        }
    }
    fputc('\n', stderr);
}

inline static void panic(char const* fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    __vreport("PANIC", fmt, ap);
    va_end(ap);
    exit(PANIC_EXIT_CODE);
}
inline static void error(char const* fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    __vreport("ERROR", fmt, ap);
    va_end(ap);
}
inline static void warning(char const* fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    __vreport("WARNING", fmt, ap);
    va_end(ap);
}
inline static void info(char const* fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    __vreport("INFO", fmt, ap);
    va_end(ap);
}
inline static void trace(char const* fmt, ...) {
#if Q4_ENABLE_TRACES
    va_list ap;
    va_start(ap, fmt);
    __vreport("TRACE", fmt, ap);
    va_end(ap);
#endif
}

}