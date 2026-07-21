import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# Cấu hình trang
st.set_page_config(page_title="Mobile Game Analytics", layout="wide", initial_sidebar_state="expanded")

# Custom CSS cho KPI Cards
st.markdown("""
<style>
div[data-testid="metric-container"] {
    background-color: #f8f9fa;
    border-left: 5px solid #4e79a7;
    padding: 15px;
    border-radius: 5px;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
}
</style>
""", unsafe_allow_html=True)

# Bảng màu Tableau 10
COLORS = ['#4e79a7','#f28e2b','#59a14f','#e15759','#76b7b2','#edc948','#b07aa1','#ff9da7','#9c755f','#bab0ac']

# Đọc dữ liệu
@st.cache_data
def load_data():
    # Chuyển sang đường dẫn tương đối để chạy được trên GitHub / Streamlit Cloud
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "02_Data", "processed"))
    
    # Fallback nếu bạn up tất cả file data và code chung vào 1 thư mục gốc trên GitHub
    if not os.path.exists(base_dir):
        base_dir = current_dir

    df_user = pd.read_parquet(os.path.join(base_dir, "full_user_master.parquet"))
    df_finance = pd.read_parquet(os.path.join(base_dir, "full_daily_finance.parquet"))
    
    # Ghép 2 file nhỏ để lách luật giới hạn 25MB của GitHub Web
    df_lvl1 = pd.read_parquet(os.path.join(base_dir, "full_level_end_clean_1.parquet"))
    df_lvl2 = pd.read_parquet(os.path.join(base_dir, "full_level_end_clean_2.parquet"))
    df_level = pd.concat([df_lvl1, df_lvl2], ignore_index=True)
    
    # Pre-process dates
    df_user['event_date'] = pd.to_datetime(df_user['event_date'])
    df_finance['event_date'] = pd.to_datetime(df_finance['event_date'])
    df_level['event_date'] = pd.to_datetime(df_level['event_date'])
    
    return df_user, df_finance, df_level

df_user, df_finance, df_level = load_data()

# --- SIDEBAR (Global Filters) ---
st.sidebar.title("⚙️ Global Filters")

# Lọc Ngày
min_date, max_date = df_user['event_date'].min(), df_user['event_date'].max()
date_range = st.sidebar.date_input("Date Range", [min_date, max_date])

# Lọc Platform
platforms = df_user['platform'].dropna().unique().tolist()
selected_platforms = st.sidebar.multiselect("Platform", platforms, default=platforms)

# Lọc Quốc gia
countries = df_user['country'].dropna().unique().tolist()
selected_countries = st.sidebar.multiselect("Country (Top 20)", countries[:20], default=countries[:5])

# Áp dụng bộ lọc
if len(date_range) == 2:
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    fdf_user = df_user[(df_user['event_date'] >= start_date) & (df_user['event_date'] <= end_date)]
    fdf_finance = df_finance[(df_finance['event_date'] >= start_date) & (df_finance['event_date'] <= end_date)]
    fdf_level = df_level[(df_level['event_date'] >= start_date) & (df_level['event_date'] <= end_date)]
else:
    fdf_user, fdf_finance, fdf_level = df_user, df_finance, df_level

if selected_platforms:
    fdf_user = fdf_user[fdf_user['platform'].isin(selected_platforms)]
    fdf_level = fdf_level[fdf_level['platform'].isin(selected_platforms)]
    
if selected_countries:
    fdf_user = fdf_user[fdf_user['country'].isin(selected_countries)]
    fdf_level = fdf_level[fdf_level['country'].isin(selected_countries)]

st.sidebar.markdown("---")
st.sidebar.write(f"**Filtered Users:** {fdf_user['user_pseudo_id'].nunique():,}")
st.sidebar.write(f"**Filtered Level Logs:** {len(fdf_level):,}")

# --- TABS ---
st.title("📱 Mobile Game Analytics Dashboard")
tab1, tab2, tab3 = st.tabs(["💰 Game Economy & ROAS", "🎮 Level Funnel & Churn", "👥 Audience & Monetization"])

# ==========================================
# TAB 1: GAME ECONOMY & ROAS
# ==========================================
with tab1:
    st.header("1. Hiệu quả Tài chính & Dòng tiền")
    
    # Tính toán KPIs
    total_rev = fdf_user['total_revenue'].sum()
    total_cost = fdf_finance['total_cost'].sum()
    roas = (total_rev / total_cost) * 100 if total_cost > 0 else 0
    unique_users = fdf_user['user_pseudo_id'].nunique()
    arpu = total_rev / unique_users if unique_users > 0 else 0
    
    # ROW 1: 4 KPI CARDS
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Revenue", f"${total_rev:,.2f}")
    col2.metric("Total Cost", f"${total_cost:,.2f}")
    col3.metric("ROAS %", f"{roas:,.1f}%")
    col4.metric("ARPU (Avg Rev per User)", f"${arpu:,.4f}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ROW 2: Biểu đồ
    c1, c2 = st.columns([2, 1])
    
    # Chart 1.1: Dual-Axis Chart (Revenue vs ROAS)
    with c1:
        st.subheader("Doanh thu & ROAS theo Ngày")
        df_daily = fdf_finance.sort_values('event_date')
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        fig1.add_trace(go.Bar(x=df_daily['event_date'], y=df_daily['daily_revenue'], name="Revenue", marker_color=COLORS[0]), secondary_y=False)
        fig1.add_trace(go.Scatter(x=df_daily['event_date'], y=df_daily['roas_pct'], name="ROAS %", marker_color=COLORS[1], mode='lines+markers'), secondary_y=True)
        fig1.update_layout(height=350, margin=dict(t=10, b=30), hovermode='x unified', legend=dict(orientation="h", y=1.15))
        st.plotly_chart(fig1, use_container_width=True)
        
    # Chart 1.2: Donut Chart (IAA vs IAP)
    with c2:
        st.subheader("Cơ cấu Doanh thu (IAA vs IAP)")
        iaa = fdf_user['rev_iaa'].sum()
        iap = fdf_user['rev_iap'].sum()
        fig2 = px.pie(names=['In-App Ads (IAA)', 'In-App Purchase (IAP)'], values=[iaa, iap], hole=0.5, color_discrete_sequence=[COLORS[2], COLORS[3]])
        fig2.update_layout(height=350, margin=dict(t=10, b=30), legend=dict(orientation="h", y=1.15))
        st.plotly_chart(fig2, use_container_width=True)

    # ROW 3: Biểu đồ
    c3, c4 = st.columns(2)
    
    # Chart 1.3: Stacked Area (Revenue by Platform)
    with c3:
        st.subheader("Xu hướng Doanh thu theo Nền tảng")
        df_plat = fdf_user.groupby(['event_date', 'platform'])['total_revenue'].sum().reset_index()
        fig3 = px.area(df_plat, x="event_date", y="total_revenue", color="platform", color_discrete_sequence=COLORS)
        fig3.update_layout(height=350, margin=dict(t=10, b=30))
        st.plotly_chart(fig3, use_container_width=True)
        
    # Chart 1.4: Grouped Bar (Revenue vs Cost)
    with c4:
        st.subheader("Doanh thu vs Chi phí (Thực tế)")
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(x=df_daily['event_date'], y=df_daily['daily_revenue'], name='Revenue', marker_color=COLORS[0]))
        fig4.add_trace(go.Bar(x=df_daily['event_date'], y=df_daily['total_cost'], name='Cost', marker_color=COLORS[3]))
        fig4.update_layout(barmode='group', height=350, margin=dict(t=10, b=30), legend=dict(orientation="h", y=1.15))
        st.plotly_chart(fig4, use_container_width=True)

# ==========================================
# TAB 2: LEVEL FUNNEL & CHURN
# ==========================================
with tab2:
    st.header("2. Phân tích Level & Rời bỏ")
    
    # Tính toán KPIs
    total_attempts = len(fdf_level)
    avg_win_rate = (fdf_level['win'].sum() / total_attempts) * 100 if total_attempts > 0 else 0
    median_playtime = fdf_level['online_time'].median()
    
    # Tính Funnel Drop-off (Người dùng qua các level)
    level_users = fdf_level.groupby('level')['user_pseudo_id'].nunique().reset_index()
    if len(level_users) > 1:
        drop_off = (1 - (level_users['user_pseudo_id'].iloc[-1] / level_users['user_pseudo_id'].iloc[0])) * 100
    else:
        drop_off = 0
        
    # ROW 1: 4 KPI CARDS
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Attempts", f"{total_attempts:,}")
    col2.metric("Avg Win Rate", f"{avg_win_rate:.1f}%")
    col3.metric("Funnel Drop-off Rate", f"{drop_off:.1f}%")
    col4.metric("Median Playtime (ms)", f"{median_playtime:,.0f}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Data cho các chart Level
    df_lvl_stats = fdf_level.groupby('level').agg(
        users=('user_pseudo_id', 'nunique'),
        attempts=('user_pseudo_id', 'count'),
        wins=('win', 'sum'),
        avg_playtime=('online_time', 'median')
    ).reset_index()
    df_lvl_stats['win_rate'] = (df_lvl_stats['wins'] / df_lvl_stats['attempts']) * 100
    # Lọc lấy 20 level đầu cho dễ nhìn
    df_lvl_stats = df_lvl_stats[df_lvl_stats['level'] <= 20]
    
    # ROW 2: Biểu đồ
    c1, c2 = st.columns([1, 1])
    
    # Chart 2.1: Funnel Chart
    with c1:
        st.subheader("Phễu Người chơi (Level 1-20)")
        fig5 = go.Figure(go.Funnel(y="Level " + df_lvl_stats['level'].astype(str), x=df_lvl_stats['users'], marker={"color": COLORS[0]}))
        fig5.update_layout(height=400, margin=dict(t=10, b=30))
        st.plotly_chart(fig5, use_container_width=True)
        
    # Chart 2.2: Grouped Bar - Dual Axis (Win Rate vs Attempts)
    with c2:
        st.subheader("Độ khó: Tỷ lệ thắng vs Số lượt thử")
        fig6 = make_subplots(specs=[[{"secondary_y": True}]])
        fig6.add_trace(go.Bar(x=df_lvl_stats['level'], y=df_lvl_stats['attempts'], name="Attempts", marker_color=COLORS[4]), secondary_y=False)
        fig6.add_trace(go.Scatter(x=df_lvl_stats['level'], y=df_lvl_stats['win_rate'], name="Win Rate %", marker_color=COLORS[3], mode='lines+markers'), secondary_y=True)
        fig6.update_layout(height=400, margin=dict(t=10, b=30), legend=dict(orientation="h", y=1.15))
        st.plotly_chart(fig6, use_container_width=True)

    # ROW 3: Biểu đồ
    c3, c4 = st.columns(2)
    
    # Chart 2.3: Bubble Scatter Plot
    with c3:
        st.subheader("Phân tích Thời gian & Độ khó")
        fig7 = px.scatter(df_lvl_stats, x="avg_playtime", y="win_rate", size="users", color="level",
                          hover_name="level", size_max=40, color_continuous_scale='Viridis')
        fig7.update_layout(height=350, margin=dict(t=10, b=30))
        st.plotly_chart(fig7, use_container_width=True)
        
    # Chart 2.4: Churn Rate by Level
    with c4:
        st.subheader("Tỷ lệ rời bỏ (Drop-off Rate) qua từng Level")
        df_lvl_stats['churn_rate'] = (1 - (df_lvl_stats['users'].shift(-1) / df_lvl_stats['users'])) * 100
        fig8 = px.line(df_lvl_stats, x="level", y="churn_rate", markers=True, color_discrete_sequence=[COLORS[3]])
        fig8.update_layout(height=350, margin=dict(t=10, b=30))
        st.plotly_chart(fig8, use_container_width=True)

# ==========================================
# TAB 3: AUDIENCE & MONETIZATION
# ==========================================
with tab3:
    st.header("3. Phân khúc Khách hàng & Monetization")
    
    # Tính toán KPIs
    iap_users = fdf_user[fdf_user['rev_iap'] > 0]
    total_active = fdf_user['user_pseudo_id'].nunique()
    total_iap_users = iap_users['user_pseudo_id'].nunique()
    arppu = iap_users['rev_iap'].sum() / total_iap_users if total_iap_users > 0 else 0
    iap_conversion = (total_iap_users / total_active) * 100 if total_active > 0 else 0
    whales = fdf_user.groupby('user_pseudo_id')['rev_iap'].sum()
    whale_count = len(whales[whales > 5]) # Nạp trên $5 được coi là whale (tuỳ chỉnh)
    
    # ROW 1: 4 KPI CARDS
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Active Users", f"{total_active:,}")
    col2.metric("ARPPU (IAP Only)", f"${arppu:,.2f}")
    col3.metric("IAP Conversion Rate", f"{iap_conversion:.2f}%")
    col4.metric("Whales Count (>$5)", f"{whale_count:,}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ROW 2: Biểu đồ
    c1, c2 = st.columns([1, 1])
    
    # Chart 3.1: Treemap (Country & Platform)
    with c1:
        st.subheader("Phân bổ Doanh thu (Quốc gia > Nền tảng)")
        df_tree = fdf_user.groupby(['country', 'platform'])['total_revenue'].sum().reset_index()
        # Chỉ lấy nước có doanh thu > 0
        df_tree = df_tree[df_tree['total_revenue'] > 0]
        if not df_tree.empty:
            fig9 = px.treemap(df_tree, path=[px.Constant("World"), 'country', 'platform'], values='total_revenue', color='total_revenue', color_continuous_scale='Blues')
            fig9.update_layout(height=400, margin=dict(t=10, b=30))
            st.plotly_chart(fig9, use_container_width=True)
        else:
            st.write("Không đủ dữ liệu doanh thu cho Treemap.")
            
    # Chart 3.2: Pareto Chart (ABC Analysis)
    with c2:
        st.subheader("Phân tích Cá mập (ABC Analysis / Pareto)")
        df_pareto = fdf_user.groupby('user_pseudo_id')['total_revenue'].sum().sort_values(ascending=False).reset_index()
        df_pareto = df_pareto[df_pareto['total_revenue'] > 0]
        if not df_pareto.empty:
            df_pareto['cum_pct'] = (df_pareto['total_revenue'].cumsum() / df_pareto['total_revenue'].sum()) * 100
            # Giới hạn top 100 cho biểu đồ đỡ rối
            df_pareto_top = df_pareto.head(100)
            
            fig10 = make_subplots(specs=[[{"secondary_y": True}]])
            fig10.add_trace(go.Bar(x=df_pareto_top.index, y=df_pareto_top['total_revenue'], name="Revenue", marker_color=COLORS[0]), secondary_y=False)
            fig10.add_trace(go.Scatter(x=df_pareto_top.index, y=df_pareto_top['cum_pct'], name="Cumulative %", marker_color=COLORS[3], mode='lines'), secondary_y=True)
            fig10.add_hline(y=80, line_dash="dash", line_color="green", secondary_y=True)
            fig10.update_layout(height=400, margin=dict(t=10, b=30), legend=dict(orientation="h", y=1.15))
            st.plotly_chart(fig10, use_container_width=True)
        else:
            st.write("Không đủ dữ liệu để vẽ Pareto.")

    # ROW 3: Biểu đồ
    c3, c4 = st.columns(2)
    
    # Chart 3.3: Heatmap (Revenue by Date and Platform) - Biến tấu do thiếu session data sạch
    with c3:
        st.subheader("Hoạt động Nạp tiền (Date x Platform)")
        df_heat = fdf_user.groupby(['event_date', 'platform'])['rev_iap'].sum().reset_index()
        df_heat_pivot = df_heat.pivot(index='platform', columns='event_date', values='rev_iap').fillna(0)
        fig11 = px.imshow(df_heat_pivot, color_continuous_scale='YlGnBu', aspect="auto")
        fig11.update_layout(height=350, margin=dict(t=10, b=30))
        st.plotly_chart(fig11, use_container_width=True)
        
    # Chart 3.4: Boxplot (Revenue Distribution by Country)
    with c4:
        st.subheader("Phân phối Chi tiêu (Country)")
        # Lọc các user có nạp và thuộc top 5 country để vẽ
        top5_countries = df_user.groupby('country')['rev_iap'].sum().nlargest(5).index
        df_box = iap_users[iap_users['country'].isin(top5_countries)]
        fig12 = px.box(df_box, x="country", y="rev_iap", color="country", color_discrete_sequence=COLORS)
        fig12.update_layout(height=350, margin=dict(t=10, b=30))
        st.plotly_chart(fig12, use_container_width=True)
