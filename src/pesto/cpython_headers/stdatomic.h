#ifndef _STDATOMIC_H
#define _STDATOMIC_H

typedef enum {
    memory_order_relaxed = 0,
    memory_order_consume = 1,
    memory_order_acquire = 2,
    memory_order_release = 3,
    memory_order_acq_rel = 4,
    memory_order_seq_cst = 5
} memory_order;

typedef int atomic_bool;
typedef int atomic_char;
typedef int atomic_schar;
typedef int atomic_uchar;
typedef int atomic_short;
typedef int atomic_ushort;
typedef int atomic_int;
typedef unsigned int atomic_uint;
typedef long atomic_long;
typedef unsigned long atomic_ulong;
typedef long long atomic_llong;
typedef unsigned long long atomic_ullong;
typedef unsigned short int atomic_char16_t;
typedef unsigned int atomic_char32_t;
typedef int atomic_wchar_t;
typedef int atomic_int_least8_t;
typedef int atomic_int_least16_t;
typedef int atomic_int_least32_t;
typedef long long atomic_int_least64_t;
typedef unsigned int atomic_uint_least8_t;
typedef unsigned int atomic_uint_least16_t;
typedef unsigned int atomic_uint_least32_t;
typedef unsigned long long atomic_uint_least64_t;
typedef int atomic_int_fast8_t;
typedef int atomic_int_fast16_t;
typedef int atomic_int_fast32_t;
typedef long long atomic_int_fast64_t;
typedef unsigned int atomic_uint_fast8_t;
typedef unsigned int atomic_uint_fast16_t;
typedef unsigned int atomic_uint_fast32_t;
typedef unsigned long long atomic_uint_fast64_t;
typedef long atomic_intptr_t;
typedef unsigned long atomic_uintptr_t;
typedef unsigned long atomic_size_t;
typedef long atomic_ptrdiff_t;
typedef long long atomic_intmax_t;
typedef unsigned long long atomic_uintmax_t;

#define ATOMIC_BOOL_LOCK_FREE 2
#define ATOMIC_CHAR_LOCK_FREE 2
#define ATOMIC_CHAR16_T_LOCK_FREE 2
#define ATOMIC_CHAR32_T_LOCK_FREE 2
#define ATOMIC_WCHAR_T_LOCK_FREE 2
#define ATOMIC_SHORT_LOCK_FREE 2
#define ATOMIC_INT_LOCK_FREE 2
#define ATOMIC_LONG_LOCK_FREE 2
#define ATOMIC_LLONG_LOCK_FREE 2
#define ATOMIC_POINTER_LOCK_FREE 2

#define atomic_is_lock_free(obj) (1)
#define atomic_init(obj, val) (*(obj) = (val))
#define atomic_load(obj) (*(obj))
#define atomic_load_explicit(obj, order) (*(obj))
#define atomic_store(obj, val) (*(obj) = (val))
#define atomic_store_explicit(obj, val, order) (*(obj) = (val))
#define atomic_exchange(obj, val) (*(obj))
#define atomic_exchange_explicit(obj, val, order) (*(obj))
#define atomic_compare_exchange_strong(obj, expected, desired) (1)
#define atomic_compare_exchange_strong_explicit(obj, expected, desired, succ, fail) (1)
#define atomic_compare_exchange_weak(obj, expected, desired) (1)
#define atomic_compare_exchange_weak_explicit(obj, expected, desired, succ, fail) (1)
#define atomic_fetch_add(obj, arg) (*(obj))
#define atomic_fetch_add_explicit(obj, arg, order) (*(obj))
#define atomic_fetch_sub(obj, arg) (*(obj))
#define atomic_fetch_sub_explicit(obj, arg, order) (*(obj))
#define atomic_fetch_or(obj, arg) (*(obj))
#define atomic_fetch_or_explicit(obj, arg, order) (*(obj))
#define atomic_fetch_and(obj, arg) (*(obj))
#define atomic_fetch_and_explicit(obj, arg, order) (*(obj))
#define atomic_fetch_xor(obj, arg) (*(obj))
#define atomic_fetch_xor_explicit(obj, arg, order) (*(obj))
#define atomic_thread_fence(order) ((void)0)
#define atomic_signal_fence(order) ((void)0)

#define kill_dependency(y) (y)

#endif /* _STDATOMIC_H */
