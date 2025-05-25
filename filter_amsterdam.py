import csv

def filter_amsterdam_companies():
    # Read the input file and write to output file
    with open('ai_companies2.csv', 'r', encoding='utf-8') as infile, \
         open('ai_companies3.csv', 'w', newline='', encoding='utf-8') as outfile:
        
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        
        # Write header
        header = next(reader)
        writer.writerow(header)
        
        # Filter companies in Amsterdam
        for row in reader:
            if len(row) >= 5:  # Ensure row has enough columns
                address = row[4].lower()
                # Check if address contains 'amsterdam' and not part of another word
                if 'amsterdam' in address and not any(x in address for x in ['amsterdamse', 'amsterdammer']):
                    writer.writerow(row)

if __name__ == "__main__":
    filter_amsterdam_companies() 