import requests
from bs4 import BeautifulSoup
import smtplib, csv, schedule, time, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import config

# ------------------------ Config ------------------------ #

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
    msg['From'] = config.EMAIL_ADDRESS
    msg['To'] = config.EMAIL_ADDRESS
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
        server.starttls()
        server.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(config.EMAIL_ADDRESS, config.EMAIL_ADDRESS, text)
        server.quit()
        print(f"Email sent: {subject}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def get_price(url, retries=3):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36"
    }
    attempt = 0
    while attempt < retries:
        try:
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for the whole price
            price_whole = soup.find('span', class_='a-price-whole')
            price_fraction = soup.find('span', class_='a-price-fraction')

            if price_whole:
                # Clean the price parts (remove commas and strip spaces)
                price_whole = price_whole.get_text().strip().replace(',', '')

                # Ensure the price whole part does not have any decimal points already
                if '.' not in price_whole:
                    # If there's a fraction part (like cents), append it; otherwise, default to '.00'
                    if price_fraction:
                        price_fraction = price_fraction.get_text().strip()
                        price = f"{price_whole}.{price_fraction}"
                    else:
                        price = f"{price_whole}.00"
                else:
                    price = price_whole
                
                return float(price)

        except Exception as e:
            print(f"Error retrieving price for {url}: {e}")
            attempt += 1
            time.sleep(5)
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