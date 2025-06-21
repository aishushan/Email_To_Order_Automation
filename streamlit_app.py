import streamlit as st
from order_processor import OrderProcessor
import pandas as pd
import json
from pathlib import Path
import os
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="Email Order Processor",
    page_icon="✉️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    .st-b7 {
        color: white;
    }
    .css-1aumxhk {
        background-color: #f0f2f6;
        border: 1px solid #d6d6d6;
        border-radius: 5px;
        padding: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize processor
@st.cache_resource
def load_processor():
    return OrderProcessor()

processor = load_processor()

# Sidebar
st.sidebar.title("Input Options")
input_method = st.sidebar.radio(
    "Select input method:",
    ("Upload email file", "Paste email text", "Sample emails")
)

email_content = ""
if input_method == "Upload email file":
    uploaded_file = st.sidebar.file_uploader(
        "Choose a .txt file",
        type=["txt"],
        accept_multiple_files=False
    )
    if uploaded_file:
        email_content = uploaded_file.read().decode("utf-8")

elif input_method == "Paste email text":
    email_content = st.sidebar.text_area(
        "Paste your email content here:",
        height=250,
        placeholder="Hi there,\n\nI'd like to order 2 t-shirts...\n\nShipping address:..."
    )

else:  # Sample emails
    sample_dir = Path("data/sample_emails")
    samples = [f for f in os.listdir(sample_dir) if f.endswith('.txt')]
    selected_sample = st.sidebar.selectbox(
        "Choose a sample email:",
        samples
    )
    if st.sidebar.button("Load Sample"):
        with open(sample_dir / selected_sample, 'r') as f:
            email_content = f.read()

# Main content
st.title("✉️ Email-to-Order Processor")
st.markdown("Extract structured order data from unstructured emails")

if email_content:
    with st.spinner("Processing email..."):
        order_data = processor.process_email(email_content)
    
    tab1, tab2, tab3 = st.tabs(["📊 Order Summary", "🔍 Detailed View", "📤 Export Data"])
    
    with tab1:
        st.header("Order Summary")
        
        with st.container(border=True):
            col1, col2 = st.columns(2)
            
            with col1:
                if order_data['customer_name']['value']:
                    st.markdown(f"**👤 Customer Name:** {order_data['customer_name']['value']}")
                    st.progress(order_data['customer_name']['confidence'])
                    st.caption(f"Confidence: {order_data['customer_name']['confidence']:.0%}")
                else:
                    st.warning("No customer name identified")
            
            with col2:
                delivery_date = order_data.get('delivery_date', {})
                if delivery_date.get('value'):
                    st.markdown(f"**📅 Delivery Date:** {delivery_date['value']}")
                    st.progress(delivery_date.get('confidence', 0.0))
                    st.caption(f"Confidence: {delivery_date.get('confidence', 0.0):.0%}")
                else:
                    st.info("No delivery date specified")
        
        shipping_address = order_data.get('shipping_address', {})
        if shipping_address.get('value'):
            with st.container(border=True):
                st.markdown("**🏠 Shipping Address**")
                st.text(shipping_address['value'])
                st.progress(shipping_address.get('confidence', 0.0))
                st.caption(f"Confidence: {shipping_address.get('confidence', 0.0):.0%}")
        else:
            st.warning("No shipping address identified")
        
        if order_data['products']:
            st.subheader("🛍️ Products Ordered")
            products_df = pd.DataFrame(order_data['products'])
            products_df['total'] = products_df['quantity'] * products_df['price']
            
            st.dataframe(
                products_df.style.format({
                    'price': '${:,.2f}',
                    'total': '${:,.2f}',
                    'confidence': '{:.0%}'
                }),
                column_config={
                    "name": "Product",
                    "sku": "SKU",
                    "quantity": "Qty",
                    "price": st.column_config.NumberColumn("Price", format="$%.2f"),
                    "total": st.column_config.NumberColumn("Total", format="$%.2f"),
                    "confidence": st.column_config.ProgressColumn(
                        "Confidence",
                        format="%.0f%%",
                        min_value=0,
                        max_value=1
                    )
                },
                hide_index=True,
                use_container_width=True
            )
            
            order_total = products_df['total'].sum()
            st.success(f"**Order Total: ${order_total:,.2f}**")
        else:
            st.error("No products identified in the email")
        
        if order_data['needs_review']:
            st.error("⚠️ **This order requires manual review**", icon="⚠️")
            if st.button("Mark as Reviewed", type="primary"):
                st.success("Order marked as reviewed")
    
    with tab2:
        st.header("Detailed Extraction Results")
        
        # with st.expander("Raw JSON Output"):
        #     st.json(order_data)
        with st.expander("Raw JSON Output"):
        # Create a copy of order_data without special_instructions
            display_data = order_data.copy()
            display_data.pop('special_instructions', None)
            st.json(display_data)
        with st.expander("Original Email Content"):
            st.code(email_content, language="text")
    
    with tab3:
        st.header("Export Options")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("JSON Export")
            st.download_button(
                label="Download as JSON",
                data=json.dumps(order_data, indent=2),
                file_name=f"order_{timestamp}.json",
                mime="application/json"
            )
        
        with col2:
            st.subheader("CSV Export")
            if order_data['products']:
                products_df = pd.DataFrame(order_data['products'])
                csv = products_df.to_csv(index=False)
                st.download_button(
                    label="Download Products as CSV",
                    data=csv,
                    file_name=f"products_{timestamp}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No products to export")
        
    