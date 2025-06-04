import pandas as pd
import markdown
from weasyprint import HTML
import os
import re

def sanitize_filename(name):
    # Replace spaces and dots with underscores
    return re.sub(r'[ .]', '_', name)

def generate_cover_letter(template_path, company_data):
    # Read the template
    with open(template_path, 'r') as f:
        template = f.read()
    
    # Replace placeholders
    letter = template.replace('[Addressee]', company_data['dear_name'])
    letter = template.replace('[Company Name]', company_data['Name'])
    # Remove surrounding quotes from personalized content
    personalized_content = company_data['personalized_content'].strip('"')
    letter = letter.replace('[Company Specific Detail]', personalized_content)
    
    # Convert markdown to HTML
    html = markdown.markdown(letter)
    
    # Add some basic styling
    styled_html = f"""
    <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 2cm;
                }}
                p {{
                    margin-bottom: 1em;
                }}
                strong {{
                    font-weight: bold;
                }}
                em {{
                    font-style: italic;
                }}
                a {{
                    color: #0000EE;
                    text-decoration: underline;
                }}
                .asterisk {{
                    color: #FF0000;  /* Bright red */
                }}
            </style>
        </head>
        <body>
            {html}
        </body>
    </html>
    """
    
    # Replace URLs with clickable links (showing cleaner text)
    url_mappings = {
        "https://github.com/McFunshine/ai-email-scraper": "github.com/McFunshine/ai-email-scraper",
        "https://spencerpj.com": "spencerpj.com"
    }
    for full_url, display_url in url_mappings.items():
        styled_html = styled_html.replace(full_url, f'<a href="{full_url}">{display_url}</a>')
    
    # Replace the email with a mailto link
    email = "spencerpj@gmail.com"
    styled_html = styled_html.replace(email, f'<a href="mailto:{email}">{email}</a>')
    
    # Add styling to asterisks
    styled_html = styled_html.replace('*', '<span class="asterisk">*</span>')
    
    return styled_html

def main():
    # Read the CSV file
    df = pd.read_csv('ai_companies8.csv')
    
    # Create output directory if it doesn't exist
    os.makedirs('cover_letters', exist_ok=True)
    
    # Generate a cover letter for each company
    for _, row in df.iterrows():
        company_name = row['Name']
        filename = f"cover_letter_{sanitize_filename(company_name)}.pdf"
        output_path = os.path.join('cover_letters', filename)
        
        # Generate the HTML content
        html_content = generate_cover_letter('cover_letter.md', row)
        
        # Create PDF
        HTML(string=html_content).write_pdf(output_path)
        print(f"Generated: {filename}")

if __name__ == "__main__":
    main() 