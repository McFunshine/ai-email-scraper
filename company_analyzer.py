import os
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from dotenv import load_dotenv
import pandas as pd

# Load environment variables
load_dotenv()

# Initialize tools
search_tool = SerperDevTool()

# Create agents
company_researcher = Agent(
    role="Company Research Specialist",
    goal="Research and analyze companies to find their key AI focus areas and achievements",
    backstory="""You are an expert at analyzing AI companies and their technological focus.
    You excel at identifying key themes, achievements, and unique selling points of AI companies.""",
    tools=[search_tool],
    verbose=True
)

content_generator = Agent(
    role="Cover Letter Content Refiner",
    goal="Craft concise, professional, and genuinely interested sentences for a cover letter, specifically highlighting the company's AI focus and expressing a desire to work on their specific AI implementations.",
    backstory="""You are an expert at creating direct, authentic, and professional content for cover letters, specifically for a Dutch business audience.
    You understand that the tone should be respectful, straightforward, and avoid hyperbole or marketing jargon.
    Your primary focus is to demonstrate that the applicant has researched the company's specific AI work and is keen to engage with their technology in a hands-on capacity.
    You will avoid repeating known product features back to the company.
    You will never fabricate details about the applicant's past achievements or make generic "aligns with my interests" statements.
    Instead, you will formulate sentences that convey a genuine desire to learn from and contribute to their specific AI projects and implementations.""",
    tools=[search_tool],
    verbose=True
)

def analyze_company(company_name, website, category):
    # Create research task
    research_task = Task(
        description=f"""Research {company_name} ({website}) focusing on their AI initiatives and achievements.
        Pay special attention to their work in {category}.
        Find specific examples of their AI work and any notable achievements.
        Return a concise summary of their key AI focus areas and achievements.""",
        agent=company_researcher,
        expected_output="A concise summary of the company's AI focus and achievements"
    )

    # Create content generation task
    content_task = Task(
        description=f"""Using the research about {company_name} (focusing on their specific AI work found by the Company Research Specialist), create 1-2 concise sentences for a cover letter.
        The sentences must:
        1.  Clearly indicate that you have researched and understand a *specific aspect* of their AI implementation or focus (e.g., their approach to explainability, a particular AI tool they use, or a domain-specific AI solution). Do not simply state their product features back to them.
        2.  Express a professional and direct interest in working *with* or *on* this specific AI technology at their company.
        3.  Avoid all forms of hyperbole, marketing speak, and insincere flattery (e.g., "particularly impressed," "aligns with my interests," "keen to contribute" unless it directly refers to hands-on work with their AI code/systems).
        4.  Do NOT make up any past achievements, metrics, or experiences for the applicant. Your focus is solely on expressing interest in *their* work.
        5.  Maintain a professional and direct tone, characteristic of Dutch business communication.
        6.  The output should be a single string, suitable for direct insertion into the cover letter at the specified placeholder.
        Example of desired output style: "I was interested to see [Company Name] featured in the *Rank My AI* report — especially given your work in [specific theme, e.g., explainability or domain-specific AI], and I am keen to contribute my software engineering background to your efforts in this area."
        Another example: "Your work in [specific AI application, e.g., using AI for predictive design analytics] is particularly relevant to my desire to gain hands-on experience with real-world AI deployments."
        """,
        agent=content_generator,
        expected_output="1-2 professional sentences showing researched understanding of their specific AI focus and direct interest in working with it."
    )

    # Create crew
    crew = Crew(
        agents=[company_researcher, content_generator],
        tasks=[research_task, content_task],
        process=Process.sequential,
        verbose=True
    )

    # Execute crew
    result = crew.kickoff()
    return result

def main():
    # Read the CSV file
    df = pd.read_csv('ai_companies6.csv')
    
    # Take only the first 3 companies
    # df_subset = df.head(3).copy()
    df_subset = df.copy()
    
    # Add a new column for the personalized content
    df_subset['personalized_content'] = None
    
    # Process each company
    for index, row in df_subset.iterrows():
        print(f"\nProcessing {row['Name']}...")
        personalized_content = analyze_company(row['Name'], row['Website'], row['Category'])
        df_subset.at[index, 'personalized_content'] = personalized_content
        print(f"\nPersonalized content for {row['Name']}:")
        print(personalized_content)
        print("\n" + "="*80)
    
    # Save to new CSV file
    df_subset.to_csv('ai_companies7.csv', index=False)
    print("\nResults saved to ai_companies7.csv")

if __name__ == "__main__":
    main() 