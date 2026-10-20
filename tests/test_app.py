import unittest

from app import app, bmi_guidance, gauge_angle


class BmiAppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_initial_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("了解自己的<br><em>健康狀況。</em>", page)
        self.assertIn("計算你的 BMI", page)
        self.assertIn('label for="name"', page)
        self.assertIn('name="name" type="text" autocomplete="name"', page)
        self.assertIn('value=""', page)
        self.assertNotIn('class="result-name"', page)

    def test_calculation_and_advice(self):
        response = self.client.post("/", data={"height": "170", "weight": "65"})
        page = response.get_data(as_text=True)
        self.assertIn("22.5", page)
        self.assertIn("健康體位", page)
        self.assertIn("維持均衡飲食", page)
        self.assertNotIn('class="result-name"', page)

    def test_calculation_with_name(self):
        response = self.client.post(
            "/", data={"name": "  王小明  ", "height": "170", "weight": "65"}
        )
        page = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('value="王小明"', page)
        self.assertIn('class="result-name">王小明，你的 BMI 計算結果</p>', page)
        self.assertIn("22.5", page)

    def test_blank_name_is_optional(self):
        for name in ["", "   "]:
            with self.subTest(name=name):
                response = self.client.post(
                    "/", data={"name": name, "height": "170", "weight": "65"}
                )
                page = response.get_data(as_text=True)
                self.assertIn("YOUR RESULT", page)
                self.assertIn("22.5", page)
                self.assertNotIn('class="result-name"', page)

    def test_name_is_preserved_after_invalid_calculation(self):
        response = self.client.post(
            "/", data={"name": "王小明", "height": "", "weight": "65"}
        )
        page = response.get_data(as_text=True)
        self.assertIn('value="王小明"', page)
        self.assertIn('id="height-error"', page)
        self.assertNotIn("YOUR RESULT", page)

    def test_name_is_escaped(self):
        response = self.client.post(
            "/",
            data={
                "name": '"><script>alert(1)</script>',
                "height": "170",
                "weight": "65",
            },
        )
        page = response.get_data(as_text=True)
        self.assertNotIn("<script>", page)
        escaped_name = "&#34;&gt;&lt;script&gt;alert(1)&lt;/script&gt;"
        self.assertIn(f'value="{escaped_name}"', page)
        self.assertIn(f'{escaped_name}，你的 BMI 計算結果</p>', page)
        self.assertIn("22.5", page)

    def test_taiwan_adult_thresholds(self):
        for bmi, category in [
            (18.4, "體重過輕"),
            (18.5, "健康體位"),
            (23.9, "健康體位"),
            (24.0, "體重過重"),
            (26.9, "體重過重"),
            (27.0, "肥胖"),
        ]:
            with self.subTest(bmi=bmi):
                self.assertEqual(bmi_guidance(bmi)["label"], category)

    def test_result_color_by_category(self):
        with self.client.get("/static/style.css") as response:
            self.assertEqual(response.status_code, 200)
            stylesheet = response.get_data(as_text=True).replace("\r\n", "\n")
        warning_rule = (
            ".result-panel.low .result-number,\n"
            ".result-panel.high .result-number,\n"
            ".result-panel.low .result-label strong,\n"
            ".result-panel.high .result-label strong { color: #b42318; }"
        )
        self.assertIn(warning_rule, stylesheet)
        for weight, tone in [
            ("18.4", "low"),
            ("18.5", "healthy"),
            ("23.9", "healthy"),
            ("24.0", "high"),
            ("26.9", "high"),
            ("27.0", "high"),
            ("18.46", "healthy"),
            ("23.96", "high"),
        ]:
            with self.subTest(weight=weight):
                response = self.client.post("/", data={"height": "100", "weight": weight})
                page = response.get_data(as_text=True)
                self.assertIn(f'class="result-panel {tone}"', page)
                self.assertIn('class="result-number"', page)

    def test_gauge_angle_mapping(self):
        for bmi, angle in [(5, -90.0), (10, -90.0), (18.5, -39.0), (24, -6.0), (25, 0.0), (27, 12.0), (40, 90.0), (55, 90.0)]:
            with self.subTest(bmi=bmi):
                self.assertEqual(gauge_angle(bmi), angle)

    def test_result_renders_gauge(self):
        response = self.client.post("/", data={"height": "170", "weight": "65"})
        page = response.get_data(as_text=True)
        self.assertIn('class="gauge"', page)
        self.assertIn('class="gauge-needle" style="transform: rotate(-15.0deg);"', page)
        for segment in ["seg-low", "seg-healthy", "seg-high", "seg-obese"]:
            self.assertIn(segment, page)

    def test_invalid_fields_do_not_produce_result(self):
        for height, weight in [("", "65"), ("0", "65"), ("abc", "65"), ("170", "-2"), ("inf", "65"), ("170", "nan"), ("1e-300", "65"), ("1e308", "65"), ("1", "1e308")]:
            with self.subTest(height=height, weight=weight):
                response = self.client.post("/", data={"height": height, "weight": weight})
                page = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn('aria-invalid="true"', page)
                self.assertNotIn("YOUR RESULT", page)

    def test_input_is_escaped(self):
        response = self.client.post("/", data={"height": '<script>alert(1)</script>', "weight": "65"})
        page = response.get_data(as_text=True)
        self.assertNotIn("<script>", page)
        self.assertIn("請輸入大於 0", page)


if __name__ == "__main__":
    unittest.main()
