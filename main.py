import requests
from bs4 import BeautifulSoup
import smtplib, csv, schedule, time, os, config, threading, queue
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, scrolledtext

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
    gui_queue.put(f"Added product: {product_url} with target price ${target_price}\n")

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

    # Log the removal
    gui_queue.put(f"Removed product: {selected_url}\n")

def edit_product():
    selected = product_listbox.curselection()
    if not selected:
        messagebox.showwarning("Selection Error", "Please select a product to edit.")
        return
    
    selected_index = selected[0]
    selected_product = product_list[selected_index]
    
    # Create a new window for editing
    edit_window = tk.Toplevel(root)
    edit_window.title("Edit Product")
    
    # Labels and Entry fields pre-filled with current values
    tk.Label(edit_window, text="Product URL:").grid(row=0, column=0, padx=10, pady=5, sticky=tk.E)
    edit_url_entry = tk.Entry(edit_window, width=50)
    edit_url_entry.grid(row=0, column=1, padx=10, pady=5)
    edit_url_entry.insert(0, selected_product['url'])
    
    tk.Label(edit_window, text="Target Price:").grid(row=1, column=0, padx=10, pady=5, sticky=tk.E)
    edit_price_entry = tk.Entry(edit_window, width=20)
    edit_price_entry.grid(row=1, column=1, padx=10, pady=5, sticky=tk.W)
    edit_price_entry.insert(0, selected_product['target_price'])

    def save_edits():
        new_url = edit_url_entry.get()
        new_target_price = edit_price_entry.get()
        
        if not new_url or not new_target_price:
            messagebox.showwarning("Input Error", "Please fill in both fields.")
            return
        
        try:
            new_target_price = float(new_target_price)
        except ValueError:
            messagebox.showwarning("Input Error", "Target price must be a number.")
            return
        
        # Update the CSV file
        with open(CSV_FILE, 'r') as file:
            rows = list(csv.reader(file))
        
        with open(CSV_FILE, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Product URL", "Target Price"])  # Write header
            for row in rows[1:]:  # Skip header
                if row[0] == selected_product['url']:
                    writer.writerow([new_url, new_target_price])
                else:
                    writer.writerow(row)
        
        # Update the product list
        update_product_list()
        
        # Log the edit
        gui_queue.put(("info", f"Edited product: {selected_product['url']} to {new_url} with target price ${new_target_price}\n"))
        
        # Close the edit window
        edit_window.destroy()
    
    # Save button
    save_button = tk.Button(edit_window, text="Save", command=save_edits)
    save_button.grid(row=2, column=0, columnspan=2, pady=10)

# Function to update the product list in the listbox
def update_product_list():
    global product_list
    product_listbox.delete(0, tk.END)  # Clear listbox

     # Load products from CSV file
    with open(CSV_FILE, 'r') as file:
        reader = csv.reader(file)
        product_list = []
        for row in list(reader)[1:]:  # Skip header row
            product_list.append({
                'url': row[0],
                'target_price': float(row[1]),
                'name': ''  # Will be filled later
            })

    # Add products to the listbox
    for product in product_list:
        product_listbox.insert(tk.END, f"{product['url']} (Target: ${product['target_price']})")

# Function to append messages to the log_text with color-coding
def log_message(message_type, message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted_message = f"[{timestamp}] {message}"
    
    # Define tag based on message type
    if message_type == "info":
        tag = "info"
    elif message_type == "success":
        tag = "success"
    elif message_type == "error":
        tag = "error"
    else:
        tag = "info"  # Default tag
    
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

# Create the main window
root = tk.Tk()
root.title("Amazon Price Tracker")

# Labels and Entry fields for Product URL and Target Price
tk.Label(root, text="Product URL:").grid(row=0, column=0, padx=10, pady=5, sticky=tk.E)
url_entry = tk.Entry(root, width=50)
url_entry.grid(row=0, column=1, padx=10, pady=5)

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
product_listbox = tk.Listbox(root, width=100, height=10)
product_listbox.grid(row=3, column=0, columnspan=4, padx=10, pady=10)

# Scrollable Text area for logs/output with color-coding tags
log_text = scrolledtext.ScrolledText(root, width=100, height=15, state='disabled')
log_text.grid(row=4, column=0, columnspan=4, padx=10, pady=10)

# Define tags for color-coding
log_text.tag_config('info', foreground='blue')
log_text.tag_config('success', foreground='green')
log_text.tag_config('error', foreground='red')

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
        gui_queue.put(("success", f"Email sent: {subject}\n"))
    except Exception as e:
        gui_queue.put(("error", f"Failed to send email: {e}\n"))

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
            gui_queue.put(("error", f"Error retrieving price for {url}: {e}\n"))
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
        gui_queue.put(("error", f"Error reading CSV file: {e}\n"))
    return products

def get_product_name(url):
    """Fetch the product name from the Amazon page."""
    try:
        response = requests.get(url, headers=HEADERS)
        
        # Check if the request was successful
        if response.status_code != 200:
            gui_queue.put(("error", f"Failed to fetch page for URL: {url}, Status Code: {response.status_code}\n"))
            return "Unknown Product"
        
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for the product title by its ID
        title = soup.find(id='productTitle')
        if title:
            product_name = title.get_text().strip()
            gui_queue.put(("info", f"Fetched product name: '{product_name}' for URL: {url}\n"))
            return product_name
        else:
            gui_queue.put(("error", f"Product title not found for URL: {url}\n"))
            return "Unknown Product"
    
    except requests.exceptions.RequestException as e:
        gui_queue.put(("error", f"Request error occurred: {str(e)}\n"))
        return "Unknown Product"
    except Exception as e:
        gui_queue.put(("error", f"An error occurred while fetching product name: {str(e)}\n"))
        return "Unknown Product"
    
def check_prices():
    """Check the price of all products and send email if necessary"""
    products = read_products(CSV_FILE)
    for product in products:
        url = product['url']
        target_price = product['target_price']
        gui_queue.put(("info", f"Checking price for: {url}\n"))

        price = get_price(url)
        if price is None:
            gui_queue.put(("error", f"Could not retrieve price for {url}\n"))
            continue

        # Get product name if not already fetched
        if not product['name']:
            product['name'] = get_product_name(url)

        gui_queue.put(("info", f"Current price: ${price} | Target price: ${target_price}\n"))

        if price <= target_price:
            subject = f"Price Alert: {product['name']} is now ${price}"
            body = f"The price for '{product['name']}' has dropped to ${price}.\n\nLink: {url}"
            send_email(subject, body)
        else:
            gui_queue.put(("info", f"No price drop for '{product['name']}'.\n"))

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