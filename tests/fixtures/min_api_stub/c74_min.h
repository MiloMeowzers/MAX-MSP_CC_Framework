#pragma once
// Syntax-check stand-in for Cycling '74 min-api -- NOT min-api (Q31 / G5).
//
// The smallest surface that lets `clang++ -std=c++17 -fsyntax-only` type-check
// the three Min-DevKit templates in src/maxpat/ext_templates.py the way
// min-api would. A passing check here is not a real build: building against
// min-devkit (setup_min_devkit + build_external) is still a user check.
//
// What it models from min-api:
//   - c74_min_api.h:59,68 -- `using sample = double;` and
//     `using samples = std::array<sample, count>;`
//   - include/c74_min_operator_sample.h -- the performer selection:
//       * sample_operator<1, 1>: `auto out = self->m_min_object(in);
//         out_samps[i] = out;` -- a 1:1 operator() must return `sample`
//         (samples<1> is a std::array and cannot be assigned to a double);
//       * sample_operator<1, 0>: called with one sample, result ignored;
//       * generic: `auto out = ins.call();` then, when numouts > 0,
//         perform_copy_output with one overload for samples<N> (indexes
//         vals[chan]) and one for `const sample val`.
//   - min-devkit min.phasor~ (<0, 1>, `sample operator()()`, one control
//     inlet) and min.xfade~ (<3, 1> returning `sample`) are the reference
//     shapes tests/test_codegen_external_fixes.py keeps compiling.

#include <array>
#include <cstddef>
#include <functional>
#include <initializer_list>
#include <type_traits>
#include <utility>
#include <vector>

namespace c74 {
namespace min {

// --- samples and atoms -------------------------------------------------------

using sample = double;

template <size_t N>
using samples = std::array<sample, N>;

struct atom {
    atom(double v) : m_double(v) {}
    atom(const char* s) : m_double(0.0), m_symbol(s) {}
    operator double() const { return m_double; }

    double      m_double;
    const char* m_symbol = nullptr;
};

using atoms = std::vector<atom>;

// --- objects -----------------------------------------------------------------

struct object_base {};

template <class T>
struct object : object_base {};

using function = std::function<atoms(const atoms&, int)>;

// --- ports and handlers ------------------------------------------------------

template <class = void>
struct inlet {
    inlet(object_base*, const char*, const char* = "") {}
};

template <class = void>
struct outlet {
    outlet(object_base*, const char*, const char* = "") {}

    template <class... A>
    void send(A&&...) {}
};

template <class = void>
struct message {
    message(object_base*, const char*, function) {}
    message(object_base*, const char*, const char*, function) {}
};

template <class = void>
struct timer {
    timer(object_base*, function) {}
    void delay(double) {}
    void stop() {}
};

struct range {
    range(std::initializer_list<double>) {}
};

template <class T>
struct attribute {
    template <class... A>
    attribute(object_base*, const char*, T value, A&&...) : m_value(value) {}
    operator T() const { return m_value; }

    T m_value;
};

// --- operators ---------------------------------------------------------------

struct sample_operator_base {};

template <size_t I, size_t O>
struct sample_operator : sample_operator_base {
    static constexpr size_t input_count() { return I; }
    static constexpr size_t output_count() { return O; }
};

// --- performer selection (mirrors c74_min_operator_sample.h) -------------------

namespace stub {

template <class T, size_t... Is>
auto call(T& self, const samples<sizeof...(Is)>& ins, std::index_sequence<Is...>)
    -> decltype(self(ins[Is]...)) {
    return self(ins[Is]...);
}

template <class T, size_t N>
void copy_output(double* out_samps, const samples<N>& vals) {
    for (size_t c = 0; c < T::output_count(); ++c)
        out_samps[c] = vals[c];
}

template <class T>
void copy_output(double* out_samps, const sample val) {
    out_samps[0] = val;
}

template <class T>
void perform(T& self) {
    if constexpr (std::is_base_of<sample_operator<1, 1>, T>::value) {
        sample in = 0.0;
        double out_samps[1] = {};
        auto out = self(in);
        out_samps[0] = out;
        (void)out_samps;
    }
    else if constexpr (std::is_base_of<sample_operator<1, 0>, T>::value) {
        sample in = 0.0;
        self(in);
    }
    else {
        samples<T::input_count()> ins {};
        if constexpr (T::output_count() > 0) {
            auto out = call(self, ins, std::make_index_sequence<T::input_count()>{});
            double out_samps[T::output_count()] = {};
            copy_output<T>(out_samps, out);
            (void)out_samps;
        }
        else {
            call(self, ins, std::make_index_sequence<T::input_count()>{});
        }
    }
}

template <class T>
void check(T& self) {
    if constexpr (std::is_base_of<sample_operator_base, T>::value)
        perform(self);
}

}  // namespace stub

}  // namespace min
}  // namespace c74

// --- macros ------------------------------------------------------------------

#define MIN_DESCRIPTION static constexpr const char* class_description
#define MIN_TAGS        static constexpr const char* class_tags
#define MIN_AUTHOR      static constexpr const char* class_author

#define MIN_FUNCTION \
    [this](const c74::min::atoms& args, const int inlet) -> c74::min::atoms

#define MIN_EXTERNAL(cls) \
    void ext_main(void* p) { c74::min::stub::check(*static_cast<cls*>(p)); }
