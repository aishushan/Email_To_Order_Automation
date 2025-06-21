import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from order_processor import OrderProcessor

console = Console()

def main():
    console.print(Panel.fit("📧 Email-to-Order Automation System", style="bold blue"))
    
    processor = OrderProcessor()
    
    sample_emails_dir = Path("data/sample_emails")
    for email_file in sample_emails_dir.glob("*.txt"):
        console.print(f"\n📨 Processing {email_file.name}", style="bold")
        
        with open(email_file, 'r') as f:
            email_content = f.read()
        
        order_data = processor.process_email(email_content)
        display_results(order_data)

def display_results(order_data: dict):
    customer_table = Table(title="Customer Information", show_header=True, header_style="bold magenta")
    customer_table.add_column("Field")
    customer_table.add_column("Value")
    customer_table.add_column("Confidence")
    
    customer_table.add_row(
        "Name", 
        order_data['customer_name']['value'] or "Not found",
        f"{order_data['customer_name']['confidence']:.0%}"
    )
    
    products_table = Table(title="Products Ordered", show_header=True, header_style="bold magenta")
    products_table.add_column("SKU")
    products_table.add_column("Product")
    products_table.add_column("Quantity")
    products_table.add_column("Price")
    products_table.add_column("Confidence")
    
    for product in order_data['products']:
        products_table.add_row(
            product['sku'],
            product['name'],
            str(product['quantity']),
            f"${product['price']:.2f}",
            f"{product['confidence']:.0%}"
        )
    
    shipping_table = Table(title="Shipping Information", show_header=True, header_style="bold magenta")
    shipping_table.add_column("Field")
    shipping_table.add_column("Value")
    shipping_table.add_column("Confidence")
    
    shipping_table.add_row(
        "Address",
        order_data['shipping_address']['value'] or "Not found",
        f"{order_data['shipping_address']['confidence']:.0%}"
    )
    
    shipping_table.add_row(
        "Delivery Date",
        order_data['delivery_date']['value'] or "Not specified",
        f"{order_data['delivery_date']['confidence']:.0%}"
    )
    
    console.print(customer_table)
    console.print(products_table)
    console.print(shipping_table)
    
    if order_data['needs_review']:
        console.print(Panel.fit("⚠️ This order requires manual review", style="bold yellow"))

if __name__ == "__main__":
    main()