import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import requests
import base64

# --- ตั้งค่าหน้าเว็บ (Page Config) ---
st.set_page_config(layout="wide")

# --- ✅ ส่วนที่แก้ไข: จัดรูปภาพและข้อความให้อยู่บรรทัดเดียวกัน ---
col1, col2 = st.columns([1, 10])

with col1:
    st.image("https://raw.githubusercontent.com/daemuktnant-MFC/streamlit-assets/main/Driver_pic.png", width=110)

with col2:
    # เปลี่ยนจาก st.title เป็น st.header เพื่อให้ขนาดใกล้เคียงกับรูปภาพที่จัดวาง
    # หรือใช้ st.markdown("<h1 style='margin-top: 0;'>MFC SD Monitoring Dashboard</h1>", unsafe_allow_html=True)
    # แต่ st.header น่าจะเหมาะสมที่สุดสำหรับการจัดวางแนวนอน
    st.header("MFC ND Monitoring Dashboard")

# -----------------------------------------------------------------
# --- ฟังก์ชันสำหรับโหลดรูปภาพ ---
# -----------------------------------------------------------------
@st.cache_data(show_spinner=False)
def get_base64_image(img_source): 
    data = None
    image_format = "png"
    
    # Check if the image source is a GitHub raw content URL
    if "github.com" in img_source and "blob" in img_source:
        img_source = img_source.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")

    if img_source.startswith("http"):
        try:
            response = requests.get(img_source, timeout=10, verify=False) 
            response.raise_for_status()
            data = response.content
            format_ext = img_source.split('.')[-1].lower()
            if format_ext in ['png', 'jpg', 'jpeg', 'gif']:
                 image_format = format_ext.replace('jpg', 'jpeg')
        except requests.exceptions.RequestException as e:
            st.warning(f"Error downloading image from URL: {img_source}\n{e}")
            return None
    elif img_source:
        try:
            data = base64.b64decode(img_source)
        except Exception:
            st.warning("Invalid base64 image data.")
            return None
    
    if data:
        return f"data:image/{image_format};base64,{base64.b64encode(data).decode()}"
    return None

@st.cache_data(show_spinner=False)
def load_image_from_source(img_source):
    if img_source and (img_source.startswith("http") or len(img_source) > 100):
        return get_base64_image(img_source)
    return None

# URL รูปภาพ (แก้ไขเป็น Raw Content Link ของ GitHub)
ROBOT_IMAGE_URL = "https://raw.githubusercontent.com/daemuktnant-MFC/streamlit-assets/main/Robot_ND.png"

# --- ฟังก์ชันสำหรับโหลดข้อมูลจากไฟล์ Excel ---
@st.cache_data
def load_data(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file, engine='openpyxl', sheet_name='OrderReport')
        return df
    except ValueError as e:
        if "Worksheet named 'OrderReport' not found" in str(e):
            st.error("ไม่พบชีต 'OrderReport' ในไฟล์ Excel ที่คุณอัปโหลด")
        else:
            st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์: {e}")
        return None
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดที่ไม่คาดคิด: {e}")
        return None

# --- Sidebar สำหรับอัปโหลดไฟล์ ---
st.sidebar.header("Upload File")
uploaded_file = st.sidebar.file_uploader(
    "กรุณาเลือกไฟล์ 'ND update' (.xlsx, .xls)", 
    type=["xlsx", "xls"]
)

# --- ตรวจสอบว่ามีการอัปโหลดไฟล์หรือไม่ ---
if uploaded_file is not None:
    
    df = load_data(uploaded_file)

    if df is not None:
        
        # --- 1. กำหนดชื่อคอลัมน์ (สำคัญมาก) ---
        COL_SLOT_TIME = 'Slot Time'
        COL_ORDER_TYPE = 'OD Type'
        COL_STATUS = 'Status'
        COL_VALUE = 'Order Value'
        COL_DRIVER = 'Driver'

        REQUIRED_COLS = [COL_SLOT_TIME, COL_ORDER_TYPE, COL_STATUS, COL_VALUE, COL_DRIVER]
        missing_cols = [col for col in REQUIRED_COLS if col not in df.columns]
        
        if missing_cols:
            st.error(f"ไม่พบคอลัมน์ที่จำเป็นในไฟล์ Excel ของคุณ: {', '.join(missing_cols)}")
            st.warning(f"กรุณาตรวจสอบว่าชื่อ Header ในไฟล์ Excel ตรงกับที่กำหนดในโค้ด (เช่น '{COL_ORDER_TYPE}', '{COL_STATUS}' ฯลฯ)")
            st.stop()

        # --- 3. เตรียมข้อมูล และ คำนวณ KPIs ---
        df_filtered = df[df[COL_ORDER_TYPE] != 'Cancelled'].copy()

        total_orders = len(df)
        total_value = df[COL_VALUE].sum()
        total_drivers = df[COL_DRIVER].nunique()
        total_cancelled = df[df[COL_ORDER_TYPE] == 'Cancelled'].shape[0]

        valid_orders = len(df_filtered)
        delay_count = df_filtered[df_filtered[COL_STATUS] == 'Delay'].shape[0]
        
        if valid_orders > 0:
            dot_percentage = (delay_count / valid_orders) * 100
        else:
            dot_percentage = 0

        # --- แสดงผล KPIs (5 คอลัมน์) ---
        kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
        kpi1.metric("**Total Order**", f"{total_orders:,}")
        kpi2.metric("**DOT (%)**", f"{dot_percentage:.2f}%")
        kpi3.metric("**Total Cancelled**", f"{total_cancelled:,}")
        kpi4.metric("**Total Driver**", f"{total_drivers:,}")
        total_value_rounded = round(total_value)
        kpi5.metric("**Total Value**", f"{total_value_rounded:,.0f}") # เพิ่ม .2f เพื่อให้มีทศนิยม 2 ตำแหน่ง
        robot_image = load_image_from_source(ROBOT_IMAGE_URL)
        if robot_image:
            with kpi6:
                st.markdown(
                    f"""
                    <div style="text-align: right; margin-top: -10px;">
                        <img src="{robot_image}" style="max-width: 250px; border-radius: 20px;">
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        st.markdown("---")

        # -----------------------------------------------------------------
        # --- 4. แสดงผลกราฟแถวกลาง (DOT และ Total Order by Rider) ---
        # -----------------------------------------------------------------
        
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.subheader("DOT Status (Excluding Cancelled)")
            
            status_counts = df_filtered[COL_STATUS].value_counts().reset_index()
            status_counts.columns = ['Status', 'Count']
            
            color_lookup = {
                'Delay': '#FF0000', 
                'On time': '#0099FF',
                'Ontime': '#0099FF'
            } # กำหนดสีตามเงื่อนไข
            colors = [color_lookup.get(s, '#A9A9A9') for s in status_counts['Status']] # Use grey for any unknown status
            
            fig_dot = go.Figure(data=[go.Pie(
                labels=status_counts['Status'],
                values=status_counts['Count'],
                hole=0.4,
                marker=dict(colors=colors), # Manually setting the colors
                textinfo='percent',
                textposition='inside',
                insidetextorientation='horizontal',
                textfont=dict(size=40),
            )])
            
             # 🔹 เพิ่มบรรทัดนี้เพื่อ "หมุน" Pie Chart
            fig_dot.update_layout(
                showlegend=True,
                uniformtext_minsize=10,
                uniformtext_mode='hide',
                piecolorway=colors,
                legend_title_text="DOT Status",
                # มุมเริ่มต้น (องศา) - 0 คือเริ่มจากแนวตั้งบนสุด
                # หมุนตามเข็มนาฬิกา
                title="DOT Status Pie Chart",
                annotations=[dict(text='DOT', x=0.5, y=0.5, font_size=20, showarrow=False)],
            )
            fig_dot.update_traces(rotation=270)  # ✅ หมุน Pie 270 องศา (เปลี่ยนค่าตามต้องการ เช่น 0, 45, 180)
            st.plotly_chart(fig_dot, use_container_width=True)

        with chart_col2:
            st.subheader("Total Order by Driver (Stacked by Slot Time)")
            
            rider_counts = df_filtered.groupby([COL_DRIVER, COL_SLOT_TIME]).size().reset_index(name='Count')
            driver_totals = rider_counts.groupby(COL_DRIVER)['Count'].sum().reset_index()
            rider_counts = rider_counts.merge(driver_totals, on=COL_DRIVER, suffixes=('', '_Total'))
            
            top_15_drivers = driver_totals.nlargest(15, 'Count')[COL_DRIVER]
            rider_counts_top_15 = rider_counts[rider_counts[COL_DRIVER].isin(top_15_drivers)]

            # 🔹 เพิ่มการกำหนดสี Slot Time ที่นี่
            slot_colors = {
                'Slot เช้า': '#4FC3F7',
                'Slot บ่าย': '#FFD54F',
                'Slot เย็น': '#FF7043',
            }
            # 🔹 กำหนดลำดับการเรียงของ Slot Time (ซ้ายไปขวา)
            slot_order = ['Slot เช้า', 'Slot บ่าย', 'Slot เย็น']

            fig_rider = px.bar(
                rider_counts_top_15, 
                y=COL_DRIVER,
                x='Count',
                color=COL_SLOT_TIME,
                orientation='h',
                text='Count',
                title="Top 15 Drivers by Order Count (Excl. Cancelled)",
                color_discrete_map=slot_colors,  # ✅ กำหนดสีเอง
                category_orders={COL_SLOT_TIME: slot_order}  # ✅ บังคับลำดับ Stack สี
            )
            
            fig_rider.update_layout(
                yaxis={'categoryorder':'total ascending'},
                xaxis_title="Number of Orders",
                yaxis_title="Driver"
            )
            st.plotly_chart(fig_rider, use_container_width=True)

        st.markdown("---")

        # -----------------------------------------------------------------
        # --- 5. กราฟ Status Order by Driver (แก้ไขตามคำขอ) ---
        # -----------------------------------------------------------------
        st.subheader("Order Status by Driver (Excluding Cancelled)")

        df_driver_status = df_filtered.groupby([COL_DRIVER, COL_STATUS]).size().reset_index(name='Count')
        df_driver_total = df_driver_status.groupby(COL_DRIVER)['Count'].sum().reset_index(name='TotalCount')
        
        all_drivers = df_driver_total[COL_DRIVER].unique()
        all_statuses = df_driver_status[COL_STATUS].unique()

        # กำหนดสีสำหรับ Status
        status_colors = {
            'Delay': '#FF0000',       # สีแดงสำหรับ Delay
            'On time': '#0099FF',    # ตัวอย่างสีสำหรับ On time
            'Pending': '#92D050',  # ตัวอย่างสีอื่นๆ
            # เพิ่ม Status อื่นๆ และสีที่ต้องการ
        }
        # ใช้สี default ถ้าไม่มีกำหนด
        for status in all_statuses:
            if status not in status_colors:
                status_colors[status] = px.colors.qualitative.Plotly[len(status_colors) % len(px.colors.qualitative.Plotly)]


        fig_driver_status = make_subplots(specs=[[{"secondary_y": True}]])

        # 1. เพิ่มกราฟแท่ง (Stacked Bar)
        for status in all_statuses:
            df_bar = df_driver_status[df_driver_status[COL_STATUS] == status]
            df_bar_full = pd.DataFrame({COL_DRIVER: all_drivers}).merge(df_bar, on=COL_DRIVER, how='left').fillna(0)
            
            fig_driver_status.add_trace(go.Bar(
                x=df_bar_full[COL_DRIVER], 
                y=df_bar_full['Count'], 
                name=status, 
                text=df_bar_full['Count'].apply(lambda x: int(x) if x > 0 else ''),
                textposition='inside',
                marker_color=status_colors.get(status) # กำหนดสีตาม status_colors
            ), secondary_y=False)

        # 2. เพิ่มเส้นกราฟ (Total) - แก้ไขเป็น Smooth และสีแดง
        fig_driver_status.add_trace(go.Scatter(
            x=df_driver_total[COL_DRIVER], 
            y=df_driver_total['TotalCount'], 
            name="Total", 
            mode='lines+markers', # มีจุดและเส้น
            text=df_driver_total['TotalCount'],
            textposition='top center',
            line=dict(color='#FFCC66', width=4, shape='spline'), # เส้น smooth
            marker=dict(color='#00B0F0', size=4) # จุดสีแดง
        ), secondary_y=True)

        # 3. ปรับ Layout
        max_y_bar = df_driver_total['TotalCount'].max() * 1.5
        max_y_line = df_driver_total['TotalCount'].max() * 1.3
        
        fig_driver_status.update_layout(
            barmode='stack',
            xaxis_title="Driver",
            legend_title="Status",
            height=500,
            hovermode="x unified" # ปรับให้ Hover แล้วแสดงข้อมูลรวม
        )
        
        fig_driver_status.update_yaxes(
            title_text="Number of Orders", 
            secondary_y=False,
            range=[0, max_y_bar]
        )
        
        fig_driver_status.update_yaxes(
            title_text="Total Orders", 
            secondary_y=True,
            showgrid=False,
            range=[0, max_y_line]
        )
        
        st.plotly_chart(fig_driver_status, use_container_width=True)


        # --- (ทางเลือก) แสดงตารางข้อมูลดิบ ---
        with st.expander("ดูข้อมูลดิบ (Raw Data)"):
            st.dataframe(df)

else:

    st.info("👋 กรุณาอัปโหลดไฟล์ 'ND update' ของคุณที่ Sidebar ด้านซ้ายเพื่อเริ่มต้นใช้งาน")



