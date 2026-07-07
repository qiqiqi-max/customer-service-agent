import unittest

from quality_rules import inspect_quality_text


class TestQualityRules(unittest.TestCase):
    def test_detects_absolute_and_guarantee_language(self):
        result = inspect_quality_text("亲，这款商品绝对是全网最低价，保证好用。")

        self.assertEqual(result["risk_level"], "high")
        self.assertGreaterEqual(result["risk_score"], 90)
        self.assertGreaterEqual(result["hit_count"], 3)
        self.assertIn("绝对化表达", {hit["category"] for hit in result["hits"]})
        self.assertIn("过度承诺", {hit["category"] for hit in result["hits"]})

    def test_detects_custom_keywords(self):
        result = inspect_quality_text(
            "客服回复里提到了指定词。",
            extra_keywords="指定词, 其他词",
        )

        self.assertEqual(result["risk_level"], "medium")
        self.assertEqual(result["hit_count"], 1)
        self.assertEqual(result["hits"][0]["rule_id"], "custom_keyword")
        self.assertEqual(result["hits"][0]["keyword"], "指定词")

    def test_returns_no_risk_without_hits(self):
        result = inspect_quality_text("亲，这款商品可以参考详情页说明。")

        self.assertEqual(result["risk_level"], "none")
        self.assertEqual(result["risk_score"], 0)
        self.assertEqual(result["hits"], [])


if __name__ == "__main__":
    unittest.main()
