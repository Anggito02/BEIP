import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import os
from datetime import datetime
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import base64
import time

load_dotenv()

# Custom CSS for better appearance
st.set_page_config(
    page_title="Customer Database",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="auto"
)

# Apply custom CSS for better appearance
st.markdown("""
<style>
    .main-header {
        font-size: 36px !important;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 20px;
        border-bottom: 2px solid #E3F2FD;
        padding: 10px;
    }
    .sub-header {
        font-size: 24px !important;
        font-weight: bold;
        color: #0D47A1;
        padding-bottom: 10px;
        border-bottom: 2px solid #E3F2FD;
        margin-bottom: 15px;
    }
    .card {
        padding: 20px;
        margin-bottom: 20px;
    }
    .info-text {
        font-size: 16px;
        color: #424242;
    }
    .highlight {
        background-color: #E3F2FD;
        padding: 5px;
        border-radius: 5px;
    }
    .tag-item {
        display: inline-block;
        background-color: #E1F5FE;
        color: #0288D1;
        padding: 5px 10px;
        margin: 2px;
        border-radius: 15px;
        font-size: 12px;
    }
    .divider {
        height: 3px;
        background-color: #E3F2FD;
        margin: 15px 0;
    }
    .button-primary {
        background-color: #1E88E5;
        color: white;
    }
    .button-secondary {
        background-color: #90CAF9;
        color: #0D47A1;
    }
    .activity-item {
        padding: 10px;
        border-left: 3px solid #1E88E5;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Define environment variables for data paths
CUSTOMER_BUSINESS = os.getenv('CUSTOMER_BUSINESSES_DATA')
CUSTOMER_PRODUCTS = os.getenv('CUSTOMER_PRODUCTS')
KEY_PERSON = os.getenv('KEY_PERSON')
MAIN_PRODUCTS = os.getenv('MAIN_PRODUCTS')
SALES_ACTIVITY = os.getenv('SALES_ACTIVITY')

# Initialize session state for navigation
if 'page' not in st.session_state:
    st.session_state.page = 'main'
if 'selected_business' not in st.session_state:
    st.session_state.selected_business = None
if 'selected_person' not in st.session_state:
    st.session_state.selected_person = None
if 'show_loading' not in st.session_state:
    st.session_state.show_loading = False

# Create dictionary of icons
icons = {
    "business": "🏢",
    "person": "👤",
    "product": "💵",
    "sales": "💰",
    "calendar": "📅",
    "location": "📍",
    "email": "📧",
    "phone": "📞",
    "tag": "🏷️",
    "note": "📝",
    "category": "📂",
    "filter": "🔍",
    "detail": "🔎",
    "back": "⬅️",
    "add": "➕",
    "delete": "❌",
    "edit": "✏️",
    "save": "💾",
    "refresh": "🔄",
    "chart": "📊",
    "dashboard": "📈",
    "activity": "⚡",
    "clock": "⏰",
    "user": "👤",
    "status": {
        "active": "✅",
        "inactive": "❌"
    }
}

def _read_data():
    """Read and merge all data sources"""
    # Show loading spinner
    with st.spinner("Loading data..."):
        sales_df = pd.read_csv(SALES_ACTIVITY)
        custbus_df = pd.read_csv(CUSTOMER_BUSINESS)
        keyperson_df = pd.read_csv(KEY_PERSON)
        custprod_df = pd.read_csv(CUSTOMER_PRODUCTS)
        mainprod_df = pd.read_csv(MAIN_PRODUCTS)

        # Parse JSON in tags column
        custbus_df['tags'] = custbus_df['tags'].apply(lambda x: json.loads(x) if pd.notna(x) else {})
        
        # Format dates
        date_columns = ['last_activity', 'created_at', 'updated_at', 'deleted_at']
        for col in date_columns:
            if col in custbus_df.columns:
                custbus_df[col] = pd.to_datetime(custbus_df[col], errors='coerce')
        
        # Add prefixes for clarity when merging
        sales = sales_df.add_prefix("sales_")
        bus = custbus_df.add_prefix("bus_")
        person = keyperson_df.add_prefix("person_")
        prod = custprod_df.add_prefix("prod_")
        mp = mainprod_df.add_prefix("mp_")
        
        # Perform merges
        df = sales.merge(
            bus,
            left_on="sales_id_customer_businesses",
            right_on="bus_id",
            how="left",
        )
        df = df.drop(columns=["sales_id_customer_businesses"])

        df = df.merge(
            person,
            left_on="bus_id_key_person",
            right_on="person_id",
            how="left",
        )
        df = df.drop(columns=["bus_id_key_person", "person_id"])
        
        df = df.merge(
            prod,
            left_on="bus_id",
            right_on="prod_id_customer_businesses",  # Updated to match CSV structure
            how="left",
        )
        df = df.drop(columns=["prod_id_customer_businesses"])
        
        df = df.merge(
            mp,
            left_on="prod_id_main_products",
            right_on="mp_id",
            how="left",
        )
        df = df.drop(columns=["prod_id_main_products", "mp_id"])
        
        return df, bus, person, prod, mp

def _create_map(business_df):
    """Create a map with business locations"""
    # Create a map centered at the mean of our data points
    mean_lat = business_df['bus_lat'].mean()
    mean_lon = business_df['bus_lon'].mean()

    m = folium.Map(location=[mean_lat, mean_lon], zoom_start=11, max_zoom=18, min_zoom=14, control_scale=True)
    
    # Add a custom map style
    folium.TileLayer(
        tiles='https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        name='CartoDB Positron',
    ).add_to(m)
    
    # Create a marker cluster for better visualization
    from folium.plugins import MarkerCluster
    marker_cluster = MarkerCluster().add_to(m)
    
    # Add markers for each business
    for idx, row in business_df.iterrows():
        # Extract tags info for popup
        tags = row['bus_tags'] if isinstance(row['bus_tags'], dict) else {}
        size = tags.get('size', 'N/A')
        industry = tags.get('industry', 'N/A')
        
        # Create popup info with better styling
        popup_html = f"""
        <div style="width: 250px;">
            <h4 style="color: #1E88E5; margin-bottom: 10px;">{row['bus_name']}</h4>
            <p><b>Category:</b> {row['bus_category']}</p>
            <p><b>Size:</b> {size}</p>
            <p><b>Industry:</b> {industry}</p>
            </p>
        </div>
        """
        
        folium.Marker(
            location=[row['bus_lat'], row['bus_lon']],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=row['bus_name'],
            icon=folium.Icon(color="#1E88E5", icon='building', prefix='fa')
        ).add_to(marker_cluster)
    
    # Add location control
    folium.plugins.Fullscreen(position='topright').add_to(m)
    
    return m

def _create_business_stats_chart(business_df):
    """Create a bar chart showing business distribution by category"""
    category_counts = business_df['bus_category'].value_counts().reset_index()
    category_counts.columns = ['Category', 'Count']
    
    fig = px.bar(
        category_counts, 
        x='Category', 
        y='Count',
        color='Count',
        color_continuous_scale='Blues',
        title='Businesses by Category'
    )
    
    fig.update_layout(
        xaxis_title="Business Category",
        yaxis_title="Number of Businesses",
        plot_bgcolor='rgba(0,0,0,0)',
        height=400
    )
    
    return fig

def _create_activity_timeline(data_df, limit=10):
    """Create a timeline of recent activities"""
    recent_activities = data_df.sort_values('sales_created_at', ascending=False).head(limit)
    
    fig = go.Figure()
    
    for idx, row in recent_activities.iterrows():
        activity_date = pd.to_datetime(row['sales_created_at'])
        
        fig.add_trace(go.Scatter(
            x=[activity_date],
            y=[idx],
            mode='markers+text',
            marker=dict(size=15, color='#1E88E5'),
            text=[f"{row['bus_name']}"],
            textposition="middle right",
            hoverinfo='text',
            hovertext=f"Date: {activity_date.strftime('%Y-%m-%d %H:%M')}<br>Business: {row['bus_name']}<br>Activity: {row['sales_activity_description']}"
        ))
    
    fig.update_layout(
        title='Recent Activities',
        xaxis=dict(title='Date'),
        yaxis=dict(
            title='',
            showticklabels=False,
            zeroline=False
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        height=300
    )
    
    return fig

def _display_loading_spinner():
    """Display a loading spinner"""
    if st.session_state.show_loading:
        with st.spinner("Loading..."):
            time.sleep(1)
        st.session_state.show_loading = False

def _display_tags(tags_dict):
    """Display tags in a visually appealing way"""
    if not tags_dict or not isinstance(tags_dict, dict):
        return
    
    tags_html = ""
    for k, v in tags_dict.items():
        tags_html += f'<span class="tag-item">{k}: {v}</span>'
    
    st.markdown(tags_html, unsafe_allow_html=True)

def show_main_page(data, business_df):
    """Display the main page with business list and map"""
    st.markdown(f'<h1 class="main-header">{icons["dashboard"]} Customer Business Database</h1>', unsafe_allow_html=True)
    
    # Dashboard metrics
    col_metrics1, col_metrics2, col_metrics3 = st.columns(3)
    
    with col_metrics1:
        st.markdown(f"""
        <div class="card" style="text-align: center;">
            <h1 style="color: #1E88E5; font-size: 36px;">{icons["business"]} {len(business_df)}</h1>
            <p style="font-size: 18px;">Total Businesses</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_metrics2:
        # Count unique key persons
        unique_persons = business_df['bus_id_key_person'].nunique()
        st.markdown(f"""
        <div class="card" style="text-align: center;">
            <h1 style="color: #1E88E5; font-size: 36px;">{icons["person"]} {unique_persons}</h1>
            <p style="font-size: 18px;">Key Contacts</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_metrics3:
        # Count activities
        activity_count = len(data)
        st.markdown(f"""
        <div class="card" style="text-align: center;">
            <h1 style="color: #1E88E5; font-size: 36px;">{icons["activity"]} {activity_count}</h1>
            <p style="font-size: 18px;">Sales Activities</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Create a tabbed interface
    tab1, tab2 = st.tabs(["📊 Dashboard", "📋 Business Directory"])
    
    with tab1:
        st.markdown(f'<h2 class="sub-header">{icons["location"]} Business Locations</h2>', unsafe_allow_html=True)
        map_obj = _create_map(business_df)
        st_folium(map_obj, width=None, height=600)
        
        st.markdown(f'<h2 class="sub-header">{icons["chart"]} Business Statistics</h2>', unsafe_allow_html=True)
        cat_chart = _create_business_stats_chart(business_df)
        st.plotly_chart(cat_chart, use_container_width=True)
        
        # Activity timeline
        st.markdown(f'<h2 class="sub-header">{icons["activity"]} Recent Activities</h2>', unsafe_allow_html=True)
        timeline_chart = _create_activity_timeline(data)
        st.plotly_chart(timeline_chart, use_container_width=True)
    
    with tab2:
        st.markdown(f'<h2 class="sub-header">{icons["business"]} Business Directory</h2>', unsafe_allow_html=True)
        
        # Create a search box
        search_text = st.text_input(f"{icons['filter']} Search businesses by name", "")
        
        # Add filters with icons
        col_filter1, col_filter2 = st.columns(2)
        
        with col_filter1:
            categories = ['All'] + sorted(business_df['bus_category'].unique().tolist())
            selected_category = st.selectbox(f"{icons['category']} Filter by Category", categories)
        
        with col_filter2:
            # Add sorting options
            sort_options = ['Name (A-Z)', 'Name (Z-A)', 'Category', 'Last Activity (Recent First)']
            selected_sort = st.selectbox(f"{icons['filter']} Sort by", sort_options)
        
        # Apply filters
        filtered_df = business_df.copy()
        
        # Apply text search
        if search_text:
            filtered_df = filtered_df[filtered_df['bus_name'].str.contains(search_text, case=False)]
        
        if selected_category != 'All':
            filtered_df = filtered_df[filtered_df['bus_category'] == selected_category]
        
        # Apply sorting
        if selected_sort == 'Name (A-Z)':
            filtered_df = filtered_df.sort_values('bus_name')
        elif selected_sort == 'Name (Z-A)':
            filtered_df = filtered_df.sort_values('bus_name', ascending=False)
        elif selected_sort == 'Category':
            filtered_df = filtered_df.sort_values('bus_category')
        elif selected_sort == 'Last Activity (Recent First)':
            filtered_df = filtered_df.sort_values('bus_last_activity', ascending=False)
        
        st.write("---")
        
        # Display business count
        st.markdown(f"<p>Showing {len(filtered_df)} businesses</p>", unsafe_allow_html=True)
        
        # Display business list with better styling
        for idx, row in filtered_df.iterrows():
            with st.container():
                st.markdown(f"""
                <div class="card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="flex: 3;">
                            <h3 style="color: #1E88E5; margin-bottom: 5px;">{icons["business"]} {row['bus_name']}</h3>
                            <p><b>{icons["category"]} Category:</b> {row['bus_category']}</p>
                """, unsafe_allow_html=True)
                
                # Extract and display tags
                tags = row['bus_tags'] if isinstance(row['bus_tags'], dict) else {}
                
                # Display other tags
                tag_html = ""
                for k, v in tags.items():
                    tag_html += f'<span class="tag-item">{k}: {v}</span> '
                
                if tag_html:
                    st.markdown(f"""
                    <p><b>{icons["tag"]} Tags:</b> {tag_html}</p>
                    """, unsafe_allow_html=True)
                
                # Format date
                last_activity = row['bus_last_activity']
                if pd.notna(last_activity):
                    last_activity_str = pd.to_datetime(last_activity).strftime('%Y-%m-%d %H:%M')
                    st.markdown(f"""
                    <p><b>{icons["calendar"]} Last Activity:</b> {last_activity_str}</p>
                    """, unsafe_allow_html=True)
                
                st.markdown("""
                        </div>
                        <div style="flex: 1; text-align: right;">
                """, unsafe_allow_html=True)
                
                # View details button
                if st.button(f"{icons['detail']} View Details", key=f"view_{idx}"):
                    st.session_state.selected_business = row
                    st.session_state.page = 'business_detail'
                    st.session_state.show_loading = True
                    st.rerun()
                
                st.write("---")
                st.markdown("""
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

def show_business_detail(data_df, person_df, product_df, mp_df):
    """Display detailed information about a selected business"""
    business = st.session_state.selected_business
    
    # Back button with animation
    _display_loading_spinner()
    
    if st.button(f"{icons['back']} Back to Business List"):
        st.session_state.page = 'main'
        st.session_state.selected_business = None
        st.session_state.show_loading = True
        st.rerun()
    
    # Extract business
    tags = business['bus_tags'] if isinstance(business['bus_tags'], dict) else {}
    
    # Business header with
    st.markdown(f"""
    <div class="card">
        <h1 class="main-header" style="text-align: left;">
            {icons["business"]} {business['bus_name']}
        </h1>
    </div>
    """, unsafe_allow_html=True)
    
    # Create tabs for better organization
    tab1, tab2, tab3 = st.tabs(["📋 Overview", "💵 Products", "⚡ Activities"])
    
    with tab1:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f'<h2 class="sub-header">{icons["business"]} Business Information</h2>', unsafe_allow_html=True)
            
            # Create a styled card for business info
            st.markdown(f"""
            <div class="card">
                <p><b>{icons["category"]} Category:</b> {business['bus_category']}</p>
            """, unsafe_allow_html=True)
            
            # Extract and display tags
            if tags:
                st.markdown(f"<p><b>{icons['tag']} Tags:</b></p>", unsafe_allow_html=True)
                _display_tags(tags)
            
            st.markdown(f"""
                <p><b>{icons["user"]} Added By:</b> {business['bus_added_by']}</p>
                <p><b>{icons["user"]} Maintained By:</b> {business['bus_maintain_by']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Create a small map for this business
            st.markdown(f'<h2 class="sub-header">{icons["location"]} Location</h2>', unsafe_allow_html=True)
            m = folium.Map(location=[business['bus_lat'], business['bus_lon']], zoom_start=15)
            
            # Add a marker with a popup
            popup_html = f"""
            <div style="width: 200px;">
                <h4 style="color: #1E88E5; margin-bottom: 10px;">{business['bus_name']}</h4>
                <p><b>Category:</b> {business['bus_category']}</p>
            </div>
            """
            
            folium.Marker(
                location=[business['bus_lat'], business['bus_lon']],
                tooltip=business['bus_name'],
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color='red', icon='building', prefix='fa')
            ).add_to(m)
            
            # Add a circle to highlight the area
            folium.Circle(
                location=[business['bus_lat'], business['bus_lon']],
                radius=200,
                fill=True,
                color='#1E88E5',
                fill_opacity=0.2
            ).add_to(m)
            
            st_folium(m, width=None, height=600)
        
        with col2:
            # Find key person information
            key_person_id = business['bus_id_key_person']
            key_person = person_df[person_df['person_id'] == key_person_id].iloc[0] if len(person_df[person_df['person_id'] == key_person_id]) > 0 else None
            
            st.markdown(f'<h2 class="sub-header">{icons["person"]} Key Contact Person</h2>', unsafe_allow_html=True)
            
            if key_person is not None:
                st.markdown(f"""
                <div class="card">
                    <h3 style="color: #1E88E5; margin-bottom: 10px;">{key_person['person_name']}</h3>
                    <p><b>{icons["note"]} CIF:</b> {key_person['person_cif']}</p>
                """, unsafe_allow_html=True)
                
                # Add status with icon
                status = "Active" if key_person['person_is_added'] else "Inactive"
                status_icon = icons["status"]["active"] if key_person['person_is_added'] else icons["status"]["inactive"]
                st.markdown(f"""
                    <p><b>Status:</b> {status_icon} {status}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"{icons['detail']} View Contact Details", key="view_contact"):
                    st.session_state.selected_person = key_person
                    st.session_state.page = 'person_detail'
                    st.session_state.show_loading = True
                    st.rerun()
            else:
                st.markdown("""
                <div class="card" style="text-align: center; padding: 20px;">
                    <p style="color: #9E9E9E;">No key person found for this business.</p>
                </div>
                """, unsafe_allow_html=True)
    
    with tab2:
        st.markdown(f'<h2 class="sub-header">{icons["product"]} Associated Products</h2>', unsafe_allow_html=True)
        
        # Get products associated with this business
        business_id = business['bus_id']
        associated_products = product_df[product_df['prod_id_customer_businesses'] == business_id]
        
        if not associated_products.empty:
            # Create a grid of product cards
            col1, col2 = st.columns(2)
            
            for idx, prod in associated_products.iterrows():
                # Find main product details
                main_product = mp_df[mp_df['mp_id'] == prod['prod_id_main_products']].iloc[0] if len(mp_df[mp_df['mp_id'] == prod['prod_id_main_products']]) > 0 else None
                
                # Alternate between columns
                with col1 if idx % 2 == 0 else col2:
                    st.markdown(f"""
                    <div class="card">
                        <h3 style="color: #1E88E5; margin-bottom: 10px;">{icons["product"]} {main_product['mp_name'] if main_product is not None else 'Unknown Product'}</h3>
                    """, unsafe_allow_html=True)
                    
                    # Display dates with formatting
                    created_at = pd.to_datetime(prod['prod_created_at']).strftime('%Y-%m-%d') if pd.notna(prod['prod_created_at']) else 'N/A'
                    st.markdown(f"""
                        <p><b>{icons["calendar"]} Added On:</b> {created_at}</p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="card" style="text-align: center; padding: 20px;">
                <p style="color: #9E9E9E;">No products associated with this business.</p>
                <p style="font-size: 36px;">💵</p>
            </div>
            """, unsafe_allow_html=True)
    
    with tab3:
        st.markdown(f'<h2 class="sub-header">{icons["activity"]} Sales Activities</h2>', unsafe_allow_html=True)
        
        # Filter data for activities related to this business
        business_id = business['bus_id']
        business_activities = data_df[data_df['bus_id'] == business_id].sort_values('sales_created_at', ascending=False)
        
        if not business_activities.empty:
            # Add a timeline visualization
            activity_dates = []
            activity_descriptions = []
            activity_by = []
            
            for _, activity in business_activities.iterrows():
                activity_date = pd.to_datetime(activity['sales_created_at']) if pd.notna(activity['sales_created_at']) else None
                if activity_date:
                    activity_dates.append(activity_date)
                    activity_descriptions.append(activity['sales_activity_description'])
                    activity_by.append(activity['sales_activity_by'])
            
            if activity_dates:
                # Create a timeline chart
                df_timeline = pd.DataFrame({
                    'Start': activity_dates,
                    'End': activity_dates,
                    'Activity': activity_descriptions,
                    'By': activity_by
                })
                
                fig = px.timeline(
                    df_timeline, 
                    x_start='Start',
                    x_end='End',
                    y='By',
                    color='By',
                    hover_data=['Activity'],
                    labels={"Date": "Date", "By": "Sales Person"},
                    title="Sales Activity Timeline"
                )
                
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    yaxis_title='',
                    xaxis_title='Activity Date',
                    height=300
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # Display activity list
            for idx, activity in business_activities.iterrows():
                activity_date = pd.to_datetime(activity['sales_created_at']).strftime('%Y-%m-%d %H:%M') if pd.notna(activity['sales_created_at']) else 'N/A'
                
                st.markdown(f"""
                <div class="activity-item">
                    <div style="display: flex; justify-content: space-between;">
                        <div style="flex: 1;">
                            <p><b>{icons["calendar"]} {activity_date}</b></p>
                        </div>
                        <div style="flex: 3;">
                            <p>{icons["note"]} {activity['sales_activity_description']}</p>
                        </div>
                        <div style="flex: 1; text-align: right;">
                            <p>{icons["user"]} {activity['sales_activity_by']}</p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="card" style="text-align: center; padding: 20px;">
                <p style="color: #9E9E9E;">No sales activities recorded for this business.</p>
                <p style="font-size: 36px;">⚡</p>
            </div>
            """, unsafe_allow_html=True)

def show_person_detail(data_df, business_df, product_df, mp_df):
    """Display detailed information about a selected key person"""
    person = st.session_state.selected_person
    
    # Back button to return to business detail
    _display_loading_spinner()
    
    if st.button(f"{icons['back']} Back to Business Detail"):
        st.session_state.page = 'business_detail'
        st.session_state.selected_person = None
        st.session_state.show_loading = True
        st.rerun()
    
    st.markdown(f'<h1 class="main-header">{icons["person"]} Key Person: {person["person_name"]}</h1>', unsafe_allow_html=True)
    
    # Create tabs for better organization
    tab1, tab2 = st.tabs(["👤 Profile", "🏢 Associated Businesses"])
    
    with tab1:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown(f'<h2 class="sub-header">{icons["person"]} Contact Information</h2>', unsafe_allow_html=True)
            
            # Create a styled card for person info
            st.markdown(f"""
            <div class="card">
                <h3 style="color: #1E88E5; margin-bottom: 10px;">{person['person_name']}</h3>
                <p><b>{icons["note"]} CIF:</b> {person['person_cif']}</p>
            """, unsafe_allow_html=True)
            
            # Status with icon
            status = "Active" if person['person_is_added'] else "Inactive"
            status_icon = icons["status"]["active"] if person['person_is_added'] else icons["status"]["inactive"]
            status_color = "#388E3C" if person['person_is_added'] else "#D32F2F"
            
            st.markdown(f"""
                <p><b>Status:</b> <span style="color: {status_color};">{status_icon} {status}</span></p>
            """, unsafe_allow_html=True)
            
            # Format dates with icons
            created_at = pd.to_datetime(person['person_created_at']).strftime('%Y-%m-%d') if pd.notna(person['person_created_at']) else 'N/A'
            st.markdown(f"""
                <p><b>{icons["calendar"]} Added On:</b> {created_at}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Add some statistics about this person
            st.markdown(f'<h2 class="sub-header">{icons["chart"]} Contact Statistics</h2>', unsafe_allow_html=True)
            
            # Count associated businesses
            person_id = person['person_id']
            associated_businesses = business_df[business_df['bus_id_key_person'] == person_id]
            num_businesses = len(associated_businesses)
            
            # Display metrics
            st.markdown(f"""
            <div class="card" style="text-align: center;">
                <h1 style="color: #1E88E5; font-size: 36px;">{icons["business"]} {num_businesses}</h1>
                <p style="font-size: 18px;">Associated Businesses</p>
            </div>
            """, unsafe_allow_html=True)
    
    with tab2:
        # Get all businesses associated with this person
        person_id = person['person_id']
        associated_businesses = business_df[business_df['bus_id_key_person'] == person_id]
        
        if not associated_businesses.empty:
            st.markdown(f'<h2 class="sub-header">{icons["business"]} Associated Businesses</h2>', unsafe_allow_html=True)
            
            for idx, bus in associated_businesses.iterrows():
                st.markdown(f"""
                <div class="card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="flex: 3;">
                            <h3 style="color: #1E88E5; margin-bottom: 5px;">{icons["business"]} {bus['bus_name']}</h3>
                            <p><b>{icons["category"]} Category:</b> {bus['bus_category']}</p>
                """, unsafe_allow_html=True)
                
                # Extract and display tags
                tags = bus['bus_tags'] if isinstance(bus['bus_tags'], dict) else {}
                if tags:
                    st.markdown(f"<p><b>{icons['tag']} Tags:</b></p>", unsafe_allow_html=True)
                    _display_tags(tags)
                
                st.markdown("""
                        </div>
                        <div style="flex: 1; text-align: right;">
                """, unsafe_allow_html=True)
                
                if st.button(f"{icons['detail']} View Business", key=f"view_bus_{idx}"):
                    st.session_state.selected_business = bus
                    st.session_state.page = 'business_detail'
                    st.session_state.show_loading = True
                    st.rerun()
                
                st.markdown("""
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="card" style="text-align: center; padding: 20px;">
                <p style="color: #9E9E9E;">No businesses associated with this person.</p>
                <p style="font-size: 36px;">🏢</p>
            </div>
            """, unsafe_allow_html=True)

# Main application with loading animation
def main():
    # Read data
    data_df, business_df, person_df, product_df, mp_df = _read_data()
    
    # Navigation based on session state
    if st.session_state.page == 'main':
        show_main_page(data_df, business_df)
    elif st.session_state.page == 'business_detail':
        show_business_detail(data_df, person_df, product_df, mp_df)
    elif st.session_state.page == 'person_detail':
        show_person_detail(data_df, business_df, product_df, mp_df)

if __name__ == '__main__':
    main()