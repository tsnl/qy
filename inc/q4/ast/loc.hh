#pragma once

#include <string>
#include <ostream>

namespace q4 {

    struct Pos { int lineIx; int colIx; };
    struct Span { Pos first; Pos last; };
    class Source;

    class BaseFileLoc {
      private:
        Source* m_source;
      protected:
        BaseFileLoc(Source* source): m_source(source) {}
        virtual ~BaseFileLoc() = default;
      public:
        inline Source* source() const { return m_source; }
        virtual std::ostream& operator<< (std::ostream& out) const = 0;
    };
    class FileSpanLoc: public BaseFileLoc {
      private:
        Span m_span;
      public:
        inline FileSpanLoc(Source* source, Span span): BaseFileLoc(source), m_span(span) {}
        virtual ~FileSpanLoc() = default;
      public:
        Span const& data() const { return m_span; }
        std::ostream& operator<< (std::ostream& out) const override;
    };
    class FilePosLoc: public BaseFileLoc {
      private:
        Pos m_pos;
      public:
        inline FilePosLoc(Source* source, Pos pos): BaseFileLoc(source), m_pos(pos) {}
      public:
        Pos const& data() const { return m_pos; }
        std::ostream& operator<< (std::ostream& out) const override;
    };

}