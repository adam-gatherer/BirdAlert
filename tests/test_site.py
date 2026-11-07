import unittest
from pathlib import Path


SITE_PATH = Path(__file__).resolve().parents[1] / "site"


class SiteTests(unittest.TestCase):
    def test_homepage_loads_generated_configuration_and_application(self):
        html = (SITE_PATH / "index.html").read_text(encoding="utf-8")

        self.assertIn('src="config.js"', html)
        self.assertIn('src="app.js"', html)
        self.assertLess(html.index('src="config.js"'), html.index('src="app.js"'))

    def test_homepage_has_a_semantic_live_sightings_table(self):
        html = (SITE_PATH / "index.html").read_text(encoding="utf-8")
        script = (SITE_PATH / "app.js").read_text(encoding="utf-8")

        self.assertIn('<section class="live-section"', html)
        self.assertIn('<table>', html)
        self.assertIn('<caption class="visually-hidden">', html)
        self.assertIn('<tbody id="sightings"', html)
        self.assertIn('document.createElement("tr")', script)
        self.assertIn("validation-badge", script)

    def test_homepage_includes_the_data_key_overview_and_repository_footer(self):
        html = (SITE_PATH / "index.html").read_text(encoding="utf-8")

        self.assertIn('id="data-key-title"', html)
        self.assertIn("Validated", html)
        self.assertIn("Provisional", html)
        self.assertIn('id="overview-title"', html)
        self.assertIn("EventBridge starts a Lambda poll", html)
        self.assertIn('href="https://github.com/adam-gatherer/BirdAlert"', html)

    def test_styles_support_a_responsive_accessible_presentation(self):
        styles = (SITE_PATH / "styles.css").read_text(encoding="utf-8")

        self.assertIn("ui-sans-serif", styles)
        self.assertIn("@media (max-width: 560px)", styles)
        self.assertIn("@media (prefers-reduced-motion: reduce)", styles)
        self.assertIn(":focus-visible", styles)
        self.assertIn("data-label", styles)

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
