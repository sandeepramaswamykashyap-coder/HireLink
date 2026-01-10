from backend.utils.llm_client import LLMClient
from backend.utils.logger import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup, Comment
import json
import time

class PerceptionEngine:
    """
    Master of Vision: Extracts interactive elements and their semantic groupings.
    """
    def __init__(self, driver):
        self.driver = driver

    def get_semantic_map(self):
        """
        Returns a simplified text representation of the page:
        [Section: Contact Info]
        - First Name (Type: text, Selector: #id_first_name)
        - Phone Number (Type: tel, Selector: #id_phone)
        [Section: Navigation]
        - Next Step (Type: button, Selector: .btn-next)
        """
        # Find all interactive elements
        elements_map = []
        interactive_tags = ["input", "select", "textarea", "button", "label"]
        
        # 1. Identify "Target" (Modal or Main)
        try:
            target = self.driver.find_element(By.CLASS_NAME, "jobs-easy-apply-modal")
        except:
            try:
                target = self.driver.find_element(By.TAG_NAME, "form")
            except:
                target = self.driver.find_element(By.TAG_NAME, "body")

        # 2. Extract elements with context
        elements = target.find_elements(By.XPATH, ".//*")
        current_section = "General"
        
        perception_log = []
        for el in elements:
            try:
                tag = el.tag_name.lower()
                
                # Update Section context
                if tag in ["h1", "h2", "h3", "h4", "legend"]:
                    text = el.text.strip()
                    if text: current_section = text
                
                if tag in ["input", "select", "textarea", "button"]:
                    if not el.is_displayed(): continue
                    
                    # Element Details
                    e_type = el.get_attribute("type") or tag
                    e_id = el.get_attribute("id") or ""
                    e_name = el.get_attribute("name") or ""
                    e_placeholder = el.get_attribute("placeholder") or ""
                    e_label = ""
                    
                    # Find Label
                    if e_id:
                        try:
                            lbl_el = target.find_element(By.CSS_SELECTOR, f"label[for='{e_id}']")
                            e_label = lbl_el.text.strip()
                        except: pass
                    
                    if not e_label:
                        e_label = el.get_attribute("aria-label") or el.text.strip() or e_placeholder or e_name
                    
                    # Build specific CSS selector
                    selector = ""
                    if e_id: selector = f"#{e_id}"
                    elif e_name: selector = f"{tag}[name='{e_name}']"
                    else: 
                        # Fallback to positional xpath relative to target if no ID/Name
                        pass 

                    perception_log.append({
                        "section": current_section,
                        "label": e_label,
                        "type": e_type,
                        "selector": selector,
                        "value": el.get_attribute("value") if tag != "button" else ""
                    })
            except: continue
            
        return perception_log

class LLMFormFiller:
    def __init__(self, driver):
        self.driver = driver
        self.llm_client = LLMClient()
    
    def _clean_html(self, html_content):
        """
        Simplified HTML for LLM consumption:
        - Removes scripts, styles, comments, metadata.
        - Removes class attributes (often noise).
        - Keeps structure (divs, headings, forms, inputs).
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove clutter
        for element in soup(["script", "style", "meta", "noscript", "svg", "path"]):
            element.decompose()
            
        for element in soup(text=lambda text: isinstance(text, Comment)):
            element.extract()
            
        # Clean attributes
        allowed_attrs = ['id', 'name', 'type', 'placeholder', 'aria-label', 'value', 'for', 'role']
        for tag in soup.find_all(True):
            attrs = dict(tag.attrs)
            for attr in attrs:
                if attr not in allowed_attrs:
                    del tag[attr]
                    
        # Remove empty divs/spans
        for tag in soup.find_all(['div', 'span']):
            if len(tag.get_text(strip=True)) == 0 and len(tag.find_all('input')) == 0:
                tag.decompose()
                
        return str(soup)

    def extract_context(self):
        """
        Captures the relevant part of the page (Modal or Main Form).
        """
        # 1. Look for common modal classes or 'active' containers
        target_element = None
        
        # Heuristics for "Job Application Modal"
        selectors = [
            ".jobs-easy-apply-modal", # LinkedIn
            "div[role='dialog']",
            "form", 
            "main"
        ]
        
        for sel in selectors:
            try:
                els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els:
                    if el.is_displayed():
                        target_element = el
                        break
                if target_element: break
            except: pass
            
        if not target_element:
            target_element = self.driver.find_element(By.TAG_NAME, "body")
            
        html = target_element.get_attribute("outerHTML")
        return self._clean_html(html)

    def determine_actions(self, semantic_map, user_profile, smart_answers=None, last_error=None):
        if not self.llm_client.client: return None

        retry_instruction = ""
        if last_error:
            retry_instruction = f"⚠️ PREVIOUS ATTEMPT FAILED: {last_error}\n"
            
        smart_context = json.dumps(smart_answers, indent=2) if smart_answers else "None"

        prompt = f"""
        You are the Brain of an Autonomous Job Application Agent.
        
        --- MISSION ---
        Fill the form below accurately using the User Profile and Smart Answers.
        You must decide whether to Fill, Select, or Click.
        
        --- USER PROFILE ---
        {json.dumps(user_profile, indent=2)}
        
        --- SMART ANSWERS (PRIORITY) ---
        {smart_context}
        
        --- PAGE PERCEPTION (SEMANTIC MAP) ---
        {json.dumps(semantic_map, indent=2)}
        
        {retry_instruction}
        
        --- INSTRUCTIONS ---
        1. Identify required fields.
        2. Map profile values to form labels.
        3. If a field asks for a Cover Letter, use the text provided in 'cover_letter' from the User Profile.
        4. If you see a "Next", "Continue", or "Review" button, you MUST click it to proceed.
        5. If you see a "Submit" or "Apply" button and the form is filled, click it last.
        6. Return a JSON object: {{ "actions": [ {{ "type": "fill|select|click", "selector": "css_selector", "value": "str" }} ] }}
        """
        return self.llm_client.generate_json(prompt)

    def execute_actions(self, actions):
        if not actions or "actions" not in actions: return False
        from selenium.webdriver.common.action_chains import ActionChains
        
        for action in actions.get("actions", []):
            try:
                sel = action.get("selector")
                act_type = action.get("type", "fill") # fill, select, click
                
                # Find Element
                element = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                
                # Scroll to it
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                time.sleep(1)
                
                if act_type == "fill":
                    val = action.get("value")
                    element.click() # Focus
                    element.clear()
                    element.send_keys(str(val))
                    
                elif act_type == "select":
                    # Try Standard Select first
                    try:
                        s = Select(element)
                        s.select_by_visible_text(action.get("option_text"))
                    except:
                        # Fallback: Click and wait for options
                        element.click()
                        time.sleep(1)
                        # This would need more complex logic for custom selects, 
                        # but often standard selects work with .send_keys
                        element.send_keys(action.get("option_text"))
                        
                elif act_type == "click":
                    try:
                        # Try standard click
                        element.click()
                    except:
                        # Try ActionChains (Move to + Click)
                        try:
                            actions = ActionChains(self.driver)
                            actions.move_to_element(element).click().perform()
                        except:
                            # Final fallback: JS Click
                            self.driver.execute_script("arguments[0].click();", element)
                
                time.sleep(0.5) 
            except Exception as e:
                logger.error(f"Action failed {action}: {e}")
                
        return True

    def fill_form(self, user_profile, smart_answers=None, max_retries=5):
        logger.info("Initializing Autonomous Perception...")
        perception = PerceptionEngine(self.driver)
        current_error = None
        start_url = self.driver.current_url
        
        for attempt in range(max_retries):
            # 1. State Analysis
            semantic_map = perception.get_semantic_map()
            if not semantic_map:
                logger.warning("No interactive elements perceived.")
                break

            # 2. Planning
            plan = self.determine_actions(semantic_map, user_profile, smart_answers=smart_answers, last_error=current_error)
            logger.info(f"Pilot Plan (Pass {attempt+1}): {plan}")
            
            if not plan or not plan.get("actions"):
                logger.warning("Pilot found no actions to take.")
                break
            
            # 3. Execution (with navigation awareness)
            nav_button_clicked = False
            for action in plan.get("actions", []):
                sel = action.get("selector", "")
                if action.get("type") == "click":
                    if any(kw in sel.lower() for kw in ["next", "submit", "review", "continue", "apply"]):
                        nav_button_clicked = True
            
            self.execute_actions(plan)
            time.sleep(3) # Heavy UI wait

            # 4. Check State Change
            current_url = self.driver.current_url
            if current_url != start_url:
                logger.info(f"Navigation Success: {start_url} -> {current_url}")
                start_url = current_url
                continue

            # Check for validation errors via DOM
            source = self.driver.page_source.lower()
            if any(err in source for err in ["error", "required", "invalid", "correct"]):
                current_error = "Validation failure. Some fields might be missing or in wrong format."
                continue
            
            if not nav_button_clicked:
                # We filled stuff but didn't click next? Maybe it's a one-page form or we done.
                return True
                
        return True
