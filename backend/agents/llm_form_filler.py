from backend.utils.llm_client import LLMClient
from backend.utils.logger import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import json
import time

class LLMFormFiller:
    def __init__(self, driver):
        self.driver = driver
        self.llm_client = LLMClient()

    def extract_form_context(self):
        """
        Scrapes all inputs, selects, and textareas from the current page.
        Returns a simplified JSON structure representing the form.
        """
        form_elements = []
        
        # 1. Inputs
        inputs = self.driver.find_elements(By.TAG_NAME, "input")
        for idx, inp in enumerate(inputs):
            if not inp.is_displayed(): continue
            chk_type = inp.get_attribute("type")
            if chk_type == "hidden": continue
            
            label_txt = ""
            # Try to find label by 'id'
            try:
                if inp.get_attribute("id"):
                    lbl_elem = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{inp.get_attribute('id')}']")
                    label_txt = lbl_elem.text
            except: pass
            
            # Fallback: Check parent or aria-label
            if not label_txt:
                label_txt = inp.get_attribute("aria-label") or inp.get_attribute("name") or ""
                
            form_elements.append({
                "type": "input",
                "subtype": chk_type,
                "id": inp.get_attribute("id"),
                "name": inp.get_attribute("name"),
                "label": label_txt,
                "current_value": inp.get_attribute("value"),
                "idx": idx, # Selenium index reference (unstable but useful for quick debug)
                "ref_key": f"input_{idx}" 
            })

        # 2. Selects
        selects = self.driver.find_elements(By.TAG_NAME, "select")
        for idx, sel in enumerate(selects):
            if not sel.is_displayed(): continue
            
            label_txt = sel.get_attribute("name") or ""
            try:
                if sel.get_attribute("id"):
                    lbl_elem = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{sel.get_attribute('id')}']")
                    label_txt = lbl_elem.text
            except: pass
            
            # Get Options
            options = [o.text for o in sel.find_elements(By.TAG_NAME, "option") if o.text.strip()]
            
            form_elements.append({
                "type": "select",
                "id": sel.get_attribute("id"),
                "name": sel.get_attribute("name"),
                "label": label_txt,
                "options": options[:20], # Truncate massive lists
                "ref_key": f"select_{idx}"
            })
            
        return form_elements

    def determine_actions(self, form_elements, user_profile):
        """
        Uses LLM to map User Profile -> Form Elements.
        """
        if not self.llm_client.client: 
            logger.warning("No LLM Client available for Form Filling.")
            return None

        prompt = f"""
        You are an intelligent Form Filler Agent.
        
        Task: Map the User Profile data to the Form Fields.
        
        --- USER PROFILE ---
        Name: {user_profile.get('name')}
        Email: {user_profile.get('email')}
        Phone: {user_profile.get('phone')}
        Skills: {user_profile.get('skills')}
        Experience: {user_profile.get('experience')}
        Education: {user_profile.get('education')}
        Address: Bangalore, India
        Visa Sponsorship Required: No
        Notice Period: Immediate / 15 days
        
        --- FORM FIELDS (JSON) ---
        {json.dumps(form_elements, indent=2)}
        
        --- INSTRUCTIONS ---
        Return a JSON object where keys are the 'ref_key' of the field, and values are the answer.
        - For 'text' inputs: provide the string to type.
        - For 'checkbox': return true to check, false to uncheck.
        - For 'radio': return true if this specific radio button should be selected.
        - For 'select': return the EXACT option text to select.
        
        Only include fields you are confident about.
        """
        
        return self.llm_client.generate_json(prompt)

    def fill_form(self, user_profile):
        """
        Main execution method.
        """
        logger.info("Starting LLM Form Fill...")
        
        # 1. Scrape
        elements_meta = self.extract_form_context()
        if not elements_meta:
            logger.info("No visible form elements found.")
            return False
            
        # 2. Decide
        actions = self.determine_actions(elements_meta, user_profile)
        if not actions:
            logger.warning("LLM returned no actions.")
            return False
            
        logger.info(f"LLM proposed actions: {actions}")
        
        # 3. Execute
        # We need to re-find elements to avoid stale references, but using index logic from extract is simplest for v1
        # Better: Re-find by the ID/Name we stored.
        
        inputs = self.driver.find_elements(By.TAG_NAME, "input")
        selects = self.driver.find_elements(By.TAG_NAME, "select")
        
        for ref_key, value in actions.items():
            try:
                idx = int(ref_key.split('_')[1])
                el_type = ref_key.split('_')[0]
                
                element = None
                if el_type == "input" and idx < len(inputs):
                    element = inputs[idx]
                    # Check type
                    t = element.get_attribute("type")
                    if t in ["text", "email", "tel", "number", "password"]:
                        element.clear()
                        element.send_keys(str(value))
                    elif t == "checkbox":
                        if value is True and not element.is_selected(): element.click()
                        elif value is False and element.is_selected(): element.click()
                    elif t == "radio":
                        if value is True: element.click()
                        
                elif el_type == "select" and idx < len(selects):
                    element = selects[idx]
                    s = Select(element)
                    try:
                        s.select_by_visible_text(str(value))
                    except:
                        # try value match
                        s.select_by_value(str(value))
                        
            except Exception as e:
                logger.error(f"Failed to fill {ref_key}: {e}")
                
        return True
