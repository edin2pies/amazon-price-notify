import requests
from bs4 import BeautifulSoup
import smtplib, csv, schedule, time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ------------------------ Config ------------------------ #

# Email Configuration
EMAIL_ADDRESS = 'edinbeteivaz@gmail.com'
EMAIL_PASSWORD = '3tW9DYQrTY9ZRs'
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

# Header
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/85.0.4183.102 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

CSV_FILE = 'products.csv'

# -------------------------------------------------------- #

def send_email(subject, body):
    """Send an email notification."""
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = EMAIL_ADDRESS
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, text)
        server.quit()
        print(f"Email sent: {subject}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def get_price(url):
    """Fetch the current price of the Amazon product."""
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(f"Failed to fetch page for URL: {url}")
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')

        # Attempt to find the price in different possible HTML elements
        price = None
        # Common ID for price
        price_tag = soup.find(id='priceblock_ourprice') or soup.find(id='priceblock_dealprice')
        if price_tag:
            price_text = price_tag.get_text().strip()
            price = parse_price(price_text)
        else:
            # Alternative method: Look for span with class 'a-offscreen'
            price_tags = soup.find_all('span', {'class': 'a-offscreen'})
            for tag in price_tags:
                price_text = tag.get_text().strip()
                price = parse_price(price_text)
                if price:
                    break

        return price
    except Exception as e:
        print(f"Error fetching price for {url}: {e}")
        return None
    
def parse_price(price_str):
    """Parse the price string to a float"""
    try:
        # Remove currency symbols and commas
        price = price_str.replace('$', '').replace(',' '').strip()
        return float(price)
    except:
        return None
    
def read_products(csv_file):
    """Read the list of products from the CSV file."""
    products = []
    try:
        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                products.append({
                    'url': row['URL'],
                    'target_price': float(row['Target Price']),
                    'name': '' # Will be filled later
                })
    except Exception as e:
        print(f"Error reading CSV file: {e}")
    return products

def get_product_name(url):
    """Fetch the product name from the Amazon page."""
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status.code != 200:
            print(f"Failed to fetch page for URL: {url}")
            return "Unknown Product"
        
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.find(id='productTitle')
        if title:
            return title.get_text().strip()
        else:
            return "Unknown Product"
    except:
        return "Unknown Product"
    
def check_prices():
    """Check the price of all products and send email if necessary"""
    products = read_products(CSV_FILE)
    for product in products:
        url = product['url']
        target_price = product['target_price']
        print(f"Checking price for: {url}")

        price = get_price(url)
        if price is None:
            print(f"Could not retrieve price for {url}")
            continue

        # Get product name if not already fetched
        if not product['name']:
            product['name'] = get_product_name(url)

        print(f"Current price: ${price} | Target price: ${target_price}")

        if price <= target_price:
            subject = f"Price Alert: {product['name']} is now ${price}"
            body = f"The price for {product['name']} has dropped to ${price}.\n\nLink: {url}"
            send_email(subject, body)
        else:
            print(f"No price drop for {product['name']}.")

def main():
    """Main function to schedule price checks."""
    # Initial check
    check_prices()

    # Schedule to check every X hours.
    schedule.every(24).hours.do(check_prices)

    print("Price tracker is running. Press Ctrl+C to exit")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("Price tracker stopped.")

if __name__ == '__main__':
    main()