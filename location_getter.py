import os
import pandas as pd
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool, WebsiteSearchTool
from dotenv import load_dotenv
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Load environment variables
load_dotenv()

# Initialize tools
search_tool = SerperDevTool()
website_tool = WebsiteSearchTool()

# Create agents
search_agent = Agent(
    role="Web Search Specialist",
    goal="Find company addresses through web searches",
    backstory="""You are an expert at finding company information through web searches.
    You are particularly good at finding office locations and addresses.""",
    tools=[search_tool],
    verbose=True
)

address_validator = Agent(
    role="Address Validator",
    goal="Validate and format company addresses",
    backstory="""You are an expert at validating company addresses and formatting them in Dutch format.
    You can determine if an address is correct for a specific company and format it properly.""",
    verbose=True
)

reverse_validator = Agent(
    role="Reverse Address Validator",
    goal="Verify addresses by reverse searching",
    backstory="""You are an expert at verifying addresses by searching for them and confirming
    that they belong to the correct company. You are particularly good at identifying mismatches
    between addresses and company names.""",
    tools=[search_tool],
    verbose=True
)

website_address_finder = Agent(
    role="Website Address Finder",
    goal="Find addresses on company websites",
    backstory="""You are an expert at analyzing web pages to find company addresses.
    You can identify addresses in various formats and contexts on web pages.""",
    tools=[website_tool],
    verbose=True
)

contact_page_finder = Agent(
    role="Contact Page Finder",
    goal="Find contact pages on company websites",
    backstory="""You are an expert at navigating company websites to find contact pages.
    You can identify contact links and analyze contact pages for address information.""",
    tools=[website_tool],
    verbose=True
)

# Function to format address in Dutch format
def format_dutch_address(address):
    # This will be handled by the LLM in the address_validator agent
    return address

# Function to check if website is accessible
def is_website_accessible(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        }
        response = requests.get(url, headers=headers, timeout=5)
        return response.status_code != 403
    except:
        return False

# Function to process a single company
def process_company(company_name, website):
    try:
        # Create search task
        search_task = Task(
            description=f"""Search for the office address of {company_name} ({website}) in the Netherlands.
            Look for terms like 'office', 'location', 'address', 'contact'.
            Return any found address information.""",
            agent=search_agent,
            expected_output="""A string containing any found address information for the company.
            If no address is found, return 'No address found in search results.'"""
        )

        # Create validation task
        validation_task = Task(
            description=f"""Validate if the found address is correct for {company_name}.
            Format the address in Dutch format (street name number, postcode city).
            If no address is found, return 'Address Not Found'.""",
            agent=address_validator,
            expected_output="""A string containing the validated and formatted address in Dutch format.
            If no valid address is found, return 'Address Not Found'."""
        )

        # Create reverse validation task
        reverse_validation_task = Task(
            description=f"""Search for the company '{company_name}' at the address found in the previous step.
            If the company name is not found in the search results for this address, return 'Address Not Found'.
            If the company is found at this address, return the validated address.""",
            agent=reverse_validator,
            expected_output="""A string containing either the validated address or 'Address Not Found'
            if the company cannot be confirmed at the given address."""
        )

        # Create initial crew for web search
        initial_crew = Crew(
            agents=[search_agent, address_validator, reverse_validator],
            tasks=[search_task, validation_task, reverse_validation_task],
            process=Process.sequential,
            verbose=True
        )

        # Execute initial crew
        initial_result = initial_crew.kickoff()

        # Only proceed with website search if no address was found
        if "Address Not Found" in initial_result or "No address found" in initial_result:
            # Check if website is accessible before proceeding
            if not is_website_accessible(website):
                print(f"Website {website} is not accessible (403 Forbidden). Using web search results only.")
                return initial_result

            # Create website address search task
            website_address_task = Task(
                description=f"""Search the company website {website}
                for any address information. Look for terms like 'office', 'location', 'address', 'contact'.
                Return any found address information.""",
                agent=website_address_finder,
                expected_output="""A string containing any found address information from the website.
                If no address is found, return 'No address found on website.'"""
            )

            # Create contact page search task
            contact_page_task = Task(
                description=f"""If no address was found on the main website, look for a contact page on {website}.
                If a contact page is found, search it for address information.
                Return any found address information.""",
                agent=contact_page_finder,
                expected_output="""A string containing any found address information from the contact page.
                If no address is found, return 'No address found on contact page.'"""
            )

            # Create website search crew
            website_crew = Crew(
                agents=[website_address_finder, contact_page_finder],
                tasks=[website_address_task, contact_page_task],
                process=Process.sequential,
                verbose=True
            )

            # Execute website crew
            website_result = website_crew.kickoff()
            
            # If website search found an address, use it; otherwise use the initial result
            if "Address Not Found" not in website_result and "No address found" not in website_result:
                return website_result

        return initial_result

    except Exception as e:
        if "API rate limit" in str(e):
            return "API_LIMIT_REACHED"
        return f"Error: {str(e)}"

def main():
    # Read the CSV file
    df = pd.read_csv('ai_companies.csv')
    
    # Create a new dataframe starting from index 21
    df_subset = df.iloc[21:].copy()
    
    # Try to read existing results file
    try:
        existing_df = pd.read_csv('ai_companies2.csv')
        # Get the last processed index
        last_processed = existing_df.index[-1] if not existing_df.empty else -1
        # Only process companies after the last processed one
        df_subset = df.iloc[last_processed + 1:].copy()
    except FileNotFoundError:
        # If file doesn't exist, start from index 21
        df_subset = df.iloc[21:].copy()
    
    # Add address column if it doesn't exist
    if 'address' not in df_subset.columns:
        df_subset['address'] = None
    
    # Process each company
    for index, row in df_subset.iterrows():
        print(f"\nProcessing {row['Name']}...")
        address = process_company(row['Name'], row['Website'])
        df_subset.at[index, 'address'] = address
        
        # Add a small delay to avoid rate limiting
        time.sleep(2)
    
    # Append to existing file or create new one
    try:
        existing_df = pd.read_csv('ai_companies2.csv')
        # Combine existing and new results
        combined_df = pd.concat([existing_df, df_subset], ignore_index=True)
        # Save combined results
        combined_df.to_csv('ai_companies2.csv', index=False)
    except FileNotFoundError:
        # If file doesn't exist, save as new
        df_subset.to_csv('ai_companies2.csv', index=False)
    
    print("\nProcessing complete. Results saved to ai_companies2.csv")

if __name__ == "__main__":
    main() 