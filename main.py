import requests
from bs4 import BeautifulSoup
import smtplib, csv, schedule, time, os, config, threading, queue, re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog

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

# Initialize a thread-safe queue for GUI updates

gui_queue = queue.Queue()

# ------------------------ GUI Functions ------------------------ #

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
    
    # Validate the Amazon URL
    if not validate_amazon_url(product_url):
        messagebox.showwarning("Input Error", "Please enter a valid Amazon product URL.")
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

     # Log the addition
    gui_queue.put(("INFO", f"Added product: {shorten_url(product_url)} with target price ${target_price}\n"))

# Function to remove a product from the CSV
def remove_product():
    selected = product_listbox.curselection()
    if not selected:
        messagebox.showwarning("Selection Error", "Please select a product to remove.")
        return
    
    # Get selected product's URL
    selected_index = selected[0]
    selected_url = product_list[selected_index][0]
    selected_url = selected_product['url']

    # Remove the selected product from the CSV file
    with open(CSV_FILE, 'r', newline='', encoding='utf-8') as file:
        rows = list(csv.reader(file))

    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for row in rows:
            if row[0] != selected_url:
                writer.writerow(row)

    # Update the product list
    update_product_list()

    # Log the removal
    gui_queue.put(("INFO", f"Removed product: {shorten_url(selected_url)}\n"))

def edit_product():
    selected = product_listbox.curselection()
    if not selected:
        messagebox.showwarning("Selection Error", "Please select a product to edit.")
        return
    
    selected_index = selected[0]
    selected_product = product_list[selected_index]
    selected_url = selected_product['url']
    selected_target_price = selected_product['target_price']

    # Prompt user for new URL and target price
    new_url = simpledialog.askstring("Edit Product", "Enter new Product URL:", initialvalue=selected_url)
    if new_url is None:
        return  # User cancelled

    new_target_price = simpledialog.askstring("Edit Product", "Enter new Target Price:", initialvalue=str(selected_target_price))
    if new_target_price is None:
        return  # User cancelled

    # Validate inputs
    if not new_url or not new_target_price:
        messagebox.showwarning("Input Error", "Please fill in both fields.")
        return
    
    try:
        new_target_price = float(new_target_price)
    except ValueError:
        messagebox.showwarning("Input Error", "Target price must be a number.")
        return

    if not validate_amazon_url(new_url):
        messagebox.showwarning("Input Error", "Please enter a valid Amazon product URL.")
        return

    # Update the CSV file
    updated = False
    with open(CSV_FILE, 'r', newline='', encoding='utf-8') as file:
        rows = list(csv.reader(file))
    
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for row in rows:
            if row[0] == selected_url:
                writer.writerow([new_url, new_target_price])
                updated = True
            else:
                writer.writerow(row)
    
    if updated:
        # Update the product list
        update_product_list()
        # Log the edit
        gui_queue.put(("INFO", f"Edited product: {shorten_url(new_url)} with new target price ${new_target_price}\n"))
    else:
        messagebox.showerror("Edit Error", "Failed to find the selected product in the CSV file.")

# Function to update the product list in the listbox
def update_product_list():
    global product_list
    product_listbox.delete(0, tk.END)  # Clear listbox

     # Load products from CSV file
    with open(CSV_FILE, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        product_list = list(reader)[1:]  # Skip header row

    # Add products to the listbox
    for product in product_list:
        display_url = shorten_url(product[0])
        product_listbox.insert(tk.END, f"{display_url} (Target: ${product[1]})")

def shorten_url(url):
    """
    Shortens the Amazon URL to include only up to the ASIN.
    Example:
    Input: https://www.amazon.com/.../dp/B0889FJT19/ref=...
    Output: https://www.amazon.com/.../dp/B0889FJT19
    """
    match = re.match(r'(https?://www\.amazon\.com/.*/dp/[A-Z0-9]{10})', url)
    if match:
        return match.group(1)
    else:
        return url  # Return original if pattern not found

def validate_amazon_url(url):
    """Validates if the URL is a proper Amazon product URL."""
    pattern = r'^https?://www\.amazon\.com/.*/dp/[A-Z0-9]{10}.*$'
    return re.match(pattern, url) is not None

# -------------------------------------------------------- #

# Function to append messages to the log_text with color-coding
def log_message(message_type, message):
    """
    Logs messages to the scrolledtext widget with color-coding.
    message_type: "INFO", "SUCCESS", "ERROR"
    message: The message string to log
    """
        
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted_message = f"[{timestamp}] {message}"
    
    # Define tag based on message type
    if message_type == "INFO":
        tag = "INFO"
    elif message_type == "SUCCESS":
        tag = "SUCCESS"
    elif message_type == "ERROR":
        tag = "ERROR"
    else:
        tag = "INFO"  # Default tag
    
    log_text.configure(state='normal')
    log_text.insert(tk.END, formatted_message, tag)
    log_text.configure(state='disabled')
    log_text.see(tk.END)

# Function to process messages from the queue
def process_queue():
    while not gui_queue.empty():
        message_type, message = gui_queue.get()
        log_message(message_type, message)
    root.after(100, process_queue)  # Check again after 100 ms

# ------------------------ GUI Setup ------------------------ #

# Create a GUI window
root = tk.Tk()
root.title("Amazon Price Tracker")

# Define tags for color-coding
log_text = scrolledtext.ScrolledText(root, width=80, height=15, state='disabled')
log_text.grid(row=5, column=0, columnspan=4, padx=10, pady=10)

log_text.tag_config("INFO", foreground="blue")
log_text.tag_config("SUCCESS", foreground="green")
log_text.tag_config("ERROR", foreground="red")

# Labels and Entry fields for Product URL and Target Price
tk.Label(root, text="Product URL:").grid(row=0, column=0, padx=10, pady=5, sticky=tk.E)
url_entry = tk.Entry(root, width=50)
url_entry.grid(row=0, column=1, padx=10, pady=5, columnspan=2, sticky=tk.W)

tk.Label(root, text="Target Price:").grid(row=1, column=0, padx=10, pady=5, sticky=tk.E)
price_entry = tk.Entry(root, width=20)
price_entry.grid(row=1, column=1, padx=10, pady=5, sticky=tk.W)

# Buttons for adding, removing, and editing products
add_button = tk.Button(root, text="Add Product", command=add_product)
add_button.grid(row=2, column=0, padx=10, pady=10, sticky=tk.E)

remove_button = tk.Button(root, text="Remove Product", command=remove_product)
remove_button.grid(row=2, column=1, padx=10, pady=10, sticky=tk.W)

edit_button = tk.Button(root, text="Edit Product", command=edit_product)
edit_button.grid(row=2, column=2, padx=10, pady=10, sticky=tk.W)

# Add "Check Prices Now" button
check_now_button = tk.Button(root, text="Check Prices Now", command=lambda: threading.Thread(target=check_prices, daemon=True).start())
check_now_button.grid(row=2, column=3, padx=10, pady=10, sticky=tk.W)

# Listbox to display tracked products
product_listbox = tk.Listbox(root, width=80, height=10)
product_listbox.grid(row=3, column=0, columnspan=4, padx=10, pady=10)

# Initialize the product list
product_list = []
update_product_list()

# Start processing the queue
root.after(100, process_queue)

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
        # Log the email sent
        gui_queue.put(("SUCCESS", f"Email sent: {subject}\n"))
    except Exception as e:
        gui_queue.put(("ERROR", f"Failed to send email: {e}\n"))

def get_price(url, retries=3):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/85.0.4183.121 Safari/537.36"
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
            gui_queue.put(("ERROR", f"Error retrieving price for {shorten_url(url)}: {e}\n"))
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
        gui_queue.put(("ERROR", f"Error reading CSV file: {e}\n"))
    return products

def get_product_name(url):
    """Fetch the product name from the Amazon page."""
    try:
        response = requests.get(url, headers=HEADERS)
        
        # Check if the request was successful
        if response.status_code != 200:
            gui_queue.put(("ERROR", f"Failed to fetch page for URL: {shorten_url(url)}, Status Code: {response.status_code}\n"))
            return "Unknown Product"
        
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for the product title by its ID
        title = soup.find(id='productTitle')
        if title:
            product_name = title.get_text().strip()
            gui_queue.put(("INFO", f"Fetched product name: '{product_name}' for URL: {shorten_url(url)}\n"))
            return product_name
        else:
            gui_queue.put(("ERROR", f"Product title not found for URL: {shorten_url(url)}\n"))
            return "Unknown Product"
    
    except requests.exceptions.RequestException as e:
        gui_queue.put(("ERROR", f"Request error occurred: {str(e)}\n"))
        return "Unknown Product"
    except Exception as e:
        gui_queue.put(("ERROR", f"An error occurred while fetching product name: {str(e)}\n"))
        return "Unknown Product"
    
def check_prices():
    """Check the price of all products and send email if necessary"""
    products = read_products(CSV_FILE)
    for product in products:
        url = product['url']
        target_price = product['target_price']
        gui_queue.put(("INFO", f"Checking price for: {shorten_url(url)}\n"))

        price = get_price(url)
        if price is None:
            gui_queue.put(("ERROR", f"Could not retrieve price for {shorten_url(url)}\n"))
            continue

        # Get product name if not already fetched
        if not product['name']:
            product['name'] = get_product_name(url)

        gui_queue.put(("INFO", f"Current price: ${price} | Target price: ${target_price}\n"))

        if price <= target_price:
            subject = f"Price Alert: {product['name']} is now ${price}"
            body = f"The price for '{product['name']}' has dropped to ${price}.\n\nLink: {url}"
            send_email(subject, body)
        else:
            gui_queue.put(("INFO", f"No price drop for '{product['name']}'.\n"))

def schedule_checks():
    """Schedule price checks every 24 hours."""
    schedule.every(24).hours.do(check_prices)
    while True:
        schedule.run_pending()
        time.sleep(1)

def start_scheduler():
    """Start the scheduler in a separate thread."""
    scheduler_thread = threading.Thread(target=schedule_checks, daemon=True)
    scheduler_thread.start()


# -------------------------------------------------------- #

def main():
    """Main function to start the scheduler and initial price check."""
    # Start the scheduler
    start_scheduler()
    
    # Perform an initial price check
    threading.Thread(target=check_prices, daemon=True).start()
    
    # Start the GUI event loop
    root.mainloop()

# Handle closing the application gracefully
def on_closing():
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
        root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

# Start the main function in the main thread
if __name__ == '__main__':
    main()