import requests
from bs4 import BeautifulSoup
import smtplib, csv, schedule, time, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import config
import tkinter as tk
from tkinter import messagebox

# ------------------------ Config ------------------------ #

# Header
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/85.0.4183.102 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

# ------------------------ CSV Config ------------------------ #

CSV_FILE = 'products.csv'

if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Product URL", "Target Price"])

# Add products to CSV
def add_product():
    product_url = url_entry.get()
    target_price = price_entry.get()

    if not product_url or not target_price:
        messagebox.showwarning("Input Error", "Please fill in both fields.")
        return
    
    try:
        target_price = float(target_price)
    except ValueError:
        messagebox.showwarning("Input Error", "Target price must be a number.")
        return
    
    # Append the products to the CSV file
    with open(CSV_FILE, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([product_url, target_price])

    # Clear the input fields
    url_entry.delete(0, tk.END)
    price_entry.delete(0, tk.END)

    # Update the product list
    update_product_list()

# Function to remove a product from the CSV
def remove_product():
    selected = product_listbox.curselection()
    if not selected:
        messagebox.showwarning("Selection Error", "Please select a product to remove.")
        return
    
    # Get selected product's URL
    selected_index = selected[0]
    selected_url = product_list[selected_index][0]

    # Remove the selected product from the CSV file
    with open(CSV_FILE, 'r') as file:
        rows = list(csv.reader(file))

    with open(CSV_FILE, 'w', newline='') as file:
        writer = csv.writer(file)
        for row in rows:
            if row[0] != selected_url:
                writer.writerow(row)

    # Update the product list
    update_product_list()

# Function to update the product list in the listbox
def update_product_list():
    global product_list
    product_listbox.delete(0, tk.END)  # Clear listbox

    # Load products from CSV file
    with open(CSV_FILE, 'r') as file:
        reader = csv.reader(file)
        product_list = list(reader)[1:]  # Skip header row

    # Add products to the listbox
    for product in product_list:
        product_listbox.insert(tk.END, f"{product[0]} (Target: {product[1]})")

# -------------------------------------------------------- #

# GUI setup
root = tk.Tk()
root.title("Amazon Price Tracker")

# Labels and Entry fields for Product URL and Target Price
tk.Label(root, text="Product URL:").grid(row=0, column=0, padx=10, pady=5)
url_entry = tk.Entry(root, width=50)
url_entry.grid(row=0, column=1, padx=10, pady=5)

tk.Label(root, text="Target Price:").grid(row=1, column=0, padx=10, pady=5)
price_entry = tk.Entry(root, width=20)
price_entry.grid(row=1, column=1, padx=10, pady=5)

# Buttons for adding and removing products
add_button = tk.Button(root, text="Add Product", command=add_product)
add_button.grid(row=2, column=0, padx=10, pady=10)

remove_button = tk.Button(root, text="Remove Product", command=remove_product)
remove_button.grid(row=2, column=1, padx=10, pady=10)

# Listbox to display tracked products
product_listbox = tk.Listbox(root, width=80, height=10)
product_listbox.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

# Initialize the product list
product_list = []
update_product_list()

# Start the GUI loop
root.mainloop()

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
        
        # Check if the request was successful
        if response.status_code != 200:
            print(f"Failed to fetch page for URL: {url}, Status Code: {response.status_code}")
            return "Unknown Product"
        
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for the product title by its ID
        title = soup.find(id='productTitle')
        if title:
            return title.get_text().strip()
        else:
            print(f"Product title not found for URL: {url}")
            return "Unknown Product"
    
    except requests.exceptions.RequestException as e:
        print(f"Request error occurred: {str(e)}")
        return "Unknown Product"
    except Exception as e:
        print(f"An error occurred while fetching product name: {str(e)}")
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