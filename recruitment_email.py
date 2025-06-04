import os
import pandas as pd
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from dotenv import load_dotenv
import time
import html
from typing import Dict

# Load environment variables
load_dotenv()

# Initialize tools
search_tool = SerperDevTool()

# Create the search agent
search_agent = Agent(
    role="Recruitment Information Specialist",
    goal="Find company recruitment contact information",
    backstory="""You are an expert at finding company recruitment and career information.
    You are particularly good at identifying recruitment pages and contact information.""",
    tools=[search_tool],
    verbose=True
)

# Create the result analyzer agent
result_analyzer = Agent(
    role="Search Result Analyzer",
    goal="Analyze search results and identify the best career page",
    backstory="""You are an expert at analyzing search results and identifying the most relevant career pages.
    You can distinguish between official company career pages and third-party job boards.
    You prioritize direct company career pages over job board listings.""",
    verbose=True
)

def process_company(company_name: str, website: str) -> Dict[str, str]:
    """
    Process a single company to find recruitment contact information.
    
    Args:
        company_name (str): Name of the company
        website (str): Company's website URL
        
    Returns:
        Dict[str, str]: Dictionary containing found information
    """
    try:
        # Create search task
        search_task = Task(
            description=f"Use the SerperDevTool to search for '{html.escape(company_name)} careers jobs recruitment'. Return the top 5 results.",
            agent=search_agent,
            expected_output="A list of search results."
        )

        # Create analysis task
        analysis_task = Task(
            description=f"""Analyze the search results for {company_name} and identify the best career page URL.
            Prioritize:
            1. Official company career pages
            2. Direct recruitment pages
            3. Company's LinkedIn career page
            Avoid:
            - Third-party job boards (Indeed, ZipRecruiter, etc.)
            - Unrelated results
            
            If no appropriate career page is found, return the word "Unknown".
            Otherwise, return only the URL of the best career page found.""",
            agent=result_analyzer,
            expected_output="Either a single URL string of the best career page found, or the word 'Unknown' if no appropriate page is found."
        )

        # Create crew for search and analysis
        search_crew = Crew(
            agents=[search_agent, result_analyzer],
            tasks=[search_task, analysis_task],
            process=Process.sequential,
            verbose=True
        )

        # Execute search crew
        career_page_url = search_crew.kickoff()
        
        # Add a small delay to avoid rate limiting
        time.sleep(2)
        
        # Convert results to dictionary format
        return {
            "recruitment_page": career_page_url,
            "search_status": "SUCCESS" if career_page_url != "Unknown" else "FAILED",
            "confidence_score": 8 if career_page_url != "Unknown" else 0,
            "notes": f"Career page: {career_page_url}"
        }

    except Exception as e:
        if "API rate limit" in str(e):
            return {
                "recruitment_page": None,
                "search_status": "FAILED",
                "confidence_score": 0,
                "notes": f"API rate limit reached: {str(e)}"
            }
        return {
            "recruitment_page": None,
            "search_status": "FAILED",
            "confidence_score": 0,
            "notes": f"Error: {str(e)}"
        }

def main():
    # Read the CSV file
    df = pd.read_csv('ai_companies3.csv')
    
    # Add recruitment_page column if it doesn't exist
    if 'recruitment_page' not in df.columns:
        df['recruitment_page'] = None
    
    # Process each company
    for index, row in df.iterrows():
        print(f"\nProcessing {row['Name']}...")
        result = process_company(row['Name'], row['Website'])
        
        # Update dataframe with just the recruitment page
        df.at[index, 'recruitment_page'] = result['recruitment_page']
        
        # Save progress after each company
        df.to_csv('ai_companies4.csv', index=False)
    
    print("\nProcessing complete. Results saved to ai_companies4.csv")

if __name__ == "__main__":
    main()
