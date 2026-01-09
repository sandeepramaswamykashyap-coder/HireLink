import fitz  # PyMuPDF

doc = fitz.open()
page = doc.new_page()
text = """
Sandeep Ramaswamy Kashyap
Python Developer
Location: Remote

EXPERIENCE
Software Engineer at Tech Corp (2020-Present)
- Developed Python automations.
- Worked with Selenium and Flask.

EDUCATION
B.Tech in Computer Science
"""
page.insert_text((50, 50), text, fontsize=12)
doc.save("dummy_resume.pdf")
print("PDF created successfully.")
