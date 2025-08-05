from scripts.website_scrapper import extract_from_webpage
from scripts.csv_updater import update_csv       

# Main script
def main():
    extract_from_webpage()
    update_csv()

if __name__ == "__main__":
    main()