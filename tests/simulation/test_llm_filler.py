import unittest
from unittest.mock import MagicMock, patch
from backend.agents.llm_form_filler import LLMFormFiller
import json

class TestLLMFiller(unittest.TestCase):
    def setUp(self):
        self.mock_driver = MagicMock()
        self.filler = LLMFormFiller(self.mock_driver)
        # Mock LLM Client
        self.filler.llm_client = MagicMock()
        self.filler.llm_client.client = True # Mimic active client

    def test_extract_context(self):
        # Mock HTML
        html = """
        <html>
            <body>
                <form>
                    <label for="name">Name</label>
                    <input id="name" type="text" name="full_name" />
                    <script>var x=1;</script>
                    <div class="garbage"></div>
                </form>
            </body>
        </html>
        """
        # Mock driver finding body
        mock_body = MagicMock()
        mock_body.get_attribute.return_value = html
        self.mock_driver.find_element.return_value = mock_body
        
        context = self.filler.extract_context()
        print(f"Extracted Context:\n{context}")
        
        # Verify script removed
        self.assertNotIn("var x=1", context)
        # Verify input kept
        self.assertIn('input', context)
        self.assertIn('name="full_name"', context)

    def test_navigation_loop(self):
        # Mock context extraction
        self.filler.extract_context = MagicMock(return_value="<form><input name='test'></form>")
        
        # Mock LLM responses for 2 attempts
        # Attempt 1: Fill input
        # Attempt 2: Click submit
        self.filler.determine_actions = MagicMock(side_effect=[
            {"actions": [{"type": "fill", "selector": "input", "value": "Test"}]},
            {"actions": [{"type": "click", "selector": "button"}]} 
        ])
        
        # Mock Execution
        self.filler.execute_actions = MagicMock(return_value=True)
        
        # Mock Page State for Loop Break
        # 1st loop: page has no error
        # 2nd loop: page success (we break loop if return True? No, loop breaks on success condition)
        # The filler loop continues 3 times unless it returns True.
        # It returns True if no error found.
        
        # Let's mock page source to NOT show error
        self.mock_driver.page_source = "<html>Success</html>"
        
        success = self.filler.fill_form({"name": "Test"}, max_retries=2)
        
        self.assertTrue(success)
        self.assertEqual(self.filler.determine_actions.call_count, 1) # Should succeed on first try if no error
        
    def test_nav_loop_with_error(self):
        self.filler.extract_context = MagicMock(return_value="<form>Error</form>")
        
        # Mock LLM to retry
        self.filler.determine_actions = MagicMock(return_value={"actions": []})
        self.filler.execute_actions = MagicMock(return_value=True)
        
        # Page shows error first time, then success
        type(self.mock_driver).page_source = unittest.mock.PropertyMock(side_effect=["Error Detected", "Success"])
        
        success = self.filler.fill_form({}, max_retries=2)
        
        # Should call define_actions twice
        self.assertEqual(self.filler.determine_actions.call_count, 2)
        self.assertTrue(success)

if __name__ == '__main__':
    unittest.main()
