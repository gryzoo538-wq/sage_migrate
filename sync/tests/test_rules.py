import os
import sys
import unittest
from decimal import Decimal as D

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import rules  # noqa: E402

TIERS = [(D("0.25"), D("2.50")), (D("2.00"), D("3.80")), (D("999"), D("6.20"))]


class CheckDigit(unittest.TestCase):
    def test_valid(self):
        for b in ("5060123400014", "5060123400052", "4006381333931"):
            self.assertTrue(rules.valid_ean13(b), b)

    def test_invalid_check_digit(self):
        self.assertFalse(rules.valid_ean13("5060123400055"))
        self.assertFalse(rules.valid_ean13("5060123400222"))

    def test_damaged_and_wrong_length(self):
        for b in ("5.06012E+12", "", "506012340001", "50601234000144", "50601234000A4", None):
            self.assertFalse(rules.valid_ean13(b), b)

    def test_mangled_detection(self):
        self.assertTrue(rules.is_mangled("5.06012E+12"))
        self.assertFalse(rules.is_mangled("5060123400014"))

    def test_check_digit_calc(self):
        self.assertEqual(rules.check_digit("506012340001"), 4)


class Charm(unittest.TestCase):
    def test_x00_goes_to_x99(self):
        self.assertEqual(rules.charm(D("13.00")), D("13.99"))

    def test_x99_stays(self):
        self.assertEqual(rules.charm(D("12.99")), D("12.99"))

    def test_x995_goes_up_to_next(self):
        self.assertEqual(rules.charm(D("12.995")), D("13.99"))

    def test_mid_and_small(self):
        self.assertEqual(rules.charm(D("24.8292")), D("24.99"))
        self.assertEqual(rules.charm(D("0.50")), D("0.99"))
        self.assertEqual(rules.charm(D("2.6892")), D("2.99"))

    def test_just_above_x99(self):
        self.assertEqual(rules.charm(D("12.991")), D("13.99"))


class Prices(unittest.TestCase):
    def test_gross_half_up(self):
        self.assertEqual(rules.gross("10.40", "T1"), D("12.48"))
        self.assertEqual(rules.gross("1.95", "T0"), D("1.95"))
        self.assertEqual(rules.gross("2.50", "T1"), D("3.00"))
        self.assertEqual(rules.gross("0.625", "T0"), D("0.63"))

    def test_shopify_price_map(self):
        self.assertEqual(rules.shopify_price(D("18.00"), D("22.99")), D("22.99"))
        self.assertEqual(rules.shopify_price(D("15.00"), D("14.99")), D("15.00"))
        self.assertEqual(rules.shopify_price(D("11.94"), None), D("11.94"))

    def test_single_amazon(self):
        self.assertEqual(rules.amazon_price(D("22.99")), D("24.99"))
        self.assertEqual(rules.amazon_price(D("3.48")), D("3.99"))

    def test_multipack(self):
        # 2.49 * 3 * 0.92 * 1.08 = 7.4220 -> 7.99
        self.assertEqual(rules.amazon_price(D("2.49"), pack=3), D("7.99"))
        # 7.99 * 3 * .92 * 1.08 = 23.8174 -> 23.99
        self.assertEqual(rules.amazon_price(D("7.99"), pack=3), D("23.99"))

    def test_fba(self):
        self.assertEqual(rules.amazon_price(D("22.99"), fba=True, fee=D("3.80")), D("28.99"))
        self.assertEqual(rules.amazon_price(D("39.99"), fba=True, fee=D("6.20")), D("49.99"))

    def test_fee_tiers_boundaries(self):
        self.assertEqual(rules.fba_fee("0.25", TIERS), D("2.50"))
        self.assertEqual(rules.fba_fee("0.26", TIERS), D("3.80"))
        self.assertEqual(rules.fba_fee("2.00", TIERS), D("3.80"))
        self.assertEqual(rules.fba_fee("4.80", TIERS), D("6.20"))

    def test_limits(self):
        self.assertEqual(rules.amazon_limits(D("24.99"), D("22.99"), D("22.99")), (D("22.99"), D("49.98")))
        self.assertEqual(rules.amazon_limits(D("9.99"), D("8.64"), None), (D("8.64"), D("19.98")))
        self.assertEqual(rules.amazon_limits(D("7.99"), D("2.49"), D("2.49"), pack=3), (None, D("15.98")))


class Stock(unittest.TestCase):
    def test_available_floor(self):
        self.assertEqual(rules.available(24, 3), 21)
        self.assertEqual(rules.available(5, 7), 0)
        self.assertEqual(rules.available(-2, 12), 0)

    def test_channel_qty(self):
        self.assertEqual(rules.channel_qty(21), 19)
        self.assertEqual(rules.channel_qty(1), 0)
        self.assertEqual(rules.channel_qty(130, 3), 42)
        self.assertEqual(rules.channel_qty(4, 3), 0)
        self.assertEqual(rules.channel_qty(21, 1, inactive=True), 0)

    def test_kit(self):
        av = {"NHG-2001": 130, "NHG-2002": 90, "NHG-2003": 120, "NHG-3001": 14}
        self.assertEqual(rules.kit_available(av), 14)
        av["NHG-2003"] = 3
        self.assertEqual(rules.kit_available(av), 3)

    def test_sku_parsing(self):
        self.assertEqual(rules.parse_amazon_sku("NHG-1001-BLU-FBA"), ("NHG-1001-BLU", 1, True))
        self.assertEqual(rules.parse_amazon_sku("NHG-2001-X3"), ("NHG-2001", 3, False))
        self.assertEqual(rules.parse_amazon_sku("NHG-2001-X3-FBA"), ("NHG-2001", 3, True))
        self.assertEqual(rules.parse_amazon_sku("NHG-3009-1M"), ("NHG-3009-1M", 1, False))
        self.assertEqual(rules.normalise_sku("NHG 1004"), "NHG1004")
        self.assertEqual(rules.normalise_sku("nhg1002-s"), "NHG1002S")


if __name__ == "__main__":
    unittest.main()
