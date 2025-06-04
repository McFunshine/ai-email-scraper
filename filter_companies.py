import csv

def filter_companies():
    # Read the input CSV file
    with open('ai_companies5.csv', 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        # Filter out rows where rank is 0
        filtered_rows = [row for row in reader if row['rank'] != '0']
    
    # Write the filtered data to a new CSV file
    with open('ai_companies6.csv', 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
        writer.writeheader()
        writer.writerows(filtered_rows)

if __name__ == "__main__":
    filter_companies() 