from . import types
from . import scheme
import unittest


class TestTypes(unittest.TestCase):
    def test_int_types(self):
        def get_and_check_int_type(int_width_in_bits: int, is_signed: bool):
            t = types.IntType.get(int_width_in_bits, is_signed)
            self.assertTrue(isinstance(t, types.IntType))
            self.assertEqual(t.is_signed, is_signed)
            self.assertEqual(t.width_in_bits, int_width_in_bits)
            return t

        def check_caching_ok(int_width_in_bits: int, is_signed: bool, existing_t: types.BaseType):
            fresh_t = types.IntType.get(int_width_in_bits, is_signed)
            self.assertIs(fresh_t, existing_t)

        # getting and checking various types:
        constructor_tuples = [
            (8, True),
            (16, True),
            (32, True),
            (64, True),
            (8, False),
            (16, False),
            (32, False),
            (64, False)
        ]
        t_map = {
            constructor_tuple: get_and_check_int_type(*constructor_tuple)
            for constructor_tuple in constructor_tuples
        }

        # ensuring caching works:
        for constructor_tuple, existing_t in t_map.items():
            check_caching_ok(*constructor_tuple, existing_t)

    def test_float_types(self):
        def get_and_check_float_type(float_width_in_bits: int):
            t = types.FloatType.get(float_width_in_bits)
            self.assertTrue(isinstance(t, types.FloatType))
            self.assertEqual(t.width_in_bits, float_width_in_bits)
            return t

        def check_caching_ok(float_width_in_bits, existing_t):
            fresh_t = types.FloatType.get(float_width_in_bits)
            self.assertIs(fresh_t, existing_t)

        # getting and checking types:
        width_in_bits_list = [
            32, 64
        ]
        t_map = {
            width_in_bits: get_and_check_float_type(width_in_bits)
            for width_in_bits in width_in_bits_list
        }

        # ensuring caching works:
        for width_in_bits, float_t in t_map.items():
            check_caching_ok(width_in_bits, float_t)

    # TODO: test more kinds of types.
