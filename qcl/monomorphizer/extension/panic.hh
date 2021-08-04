#pragma once

#include <exception>
#include <string>

namespace monomorphizer {

    class Panic: public std::exception {
      private:
        std::string m_msg;
      public:
        Panic(std::string msg);
    };

    inline Panic::Panic(std::string msg)
    :   m_msg(std::move(msg))
    {}

}