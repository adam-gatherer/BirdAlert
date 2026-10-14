import unittest
from pathlib import Path


SITE_PATH = Path(__file__).resolve().parents[1] / "site"


class SiteTests(unittest.TestCase):
    def test_homepage_loads_generated_configuration_and_application(self):
        html = (SITE_PATH / "index.html").read_text(encoding="utf-8")

        self.assertIn('src="config.js"', html)
        self.assertIn('src="app.js"', html)
        self.assertLess(html.index('src="config.js"'), html.index('src="app.js"'))

    def test_homepage_uses_a_basic_sightings_table(self):
        html = (SITE_PATH / "index.html").read_text(encoding="utf-8")
        script = (SITE_PATH / "app.js").read_text(encoding="utf-8")

        self.assertIn("<table>", html)
        self.assertIn('<tbody id="sightings"', html)
        self.assertIn('document.createElement("tr")', script)

    def test_styles_use_a_web_one_typographic_baseline(self):
        styles = (SITE_PATH / "styles.css").read_text(encoding="utf-8")

        self.assertIn('font-family: "Times New Roman", Times, serif', styles)
        self.assertIn("border: 1px solid #000", styles)

    def test_application_fetches_once_on_page_load_without_background_polling(self):
        script = (SITE_PATH / "app.js").read_text(encoding="utf-8")

        self.assertIn("BIRDALERT_API_ENDPOINT", script)
        self.assertIn("/sightings", script)
        self.assertIn('cache: "no-store"', script)
        self.assertNotIn("setInterval", script)
        self.assertNotIn("setTimeout", script)

    def test_application_renders_location_names_without_coordinates(self):
        script = (SITE_PATH / "app.js").read_text(encoding="utf-8")

        self.assertIn("sighting.location.name", script)
        self.assertNotIn("sighting.location.latitude", script)
        self.assertNotIn("sighting.location.longitude", script)

    def test_application_displays_the_backend_processing_timestamp(self):
        html = (SITE_PATH / "index.html").read_text(encoding="utf-8")
        script = (SITE_PATH / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="freshness"', html)
        self.assertIn("last_successful_processing_at", script)
        self.assertIn("Data last processed:", script)


if __name__ == "__main__":
    unittest.main()
