import os

# Get the absolute path to the template
project_root = os.path.dirname(os.path.abspath(__file__))
template_path = os.path.join(project_root, 'templates', 'reset_password_email.html')
print(template_path)

try:
    with open(template_path, 'r') as file:
        html_template = file.read()
    print("Template read successfully")
except Exception as e:
    print(f"Error reading email template: {e}")
