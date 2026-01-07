# Mutolaa Bot - Admin Panel (Streamlit)
# Fixed version with safe division and API integration

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime

# Configuration
st.set_page_config(
    page_title="Mutolaa Admin Panel",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_URL = "http://localhost:8000/api"

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f2937;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

@st.cache_data(ttl=60)
def fetch_stats():
    try:
        response = requests.get(f"{API_URL}/stats")
        return response.json()
    except Exception as e:
        st.error(f"Error fetching stats: {e}")
        return None

@st.cache_data(ttl=60)
def fetch_users(search="", status="", limit=100):
    try:
        params = {"limit": limit}
        if search:
            params["search"] = search
        if status:
            params["status"] = status
        response = requests.get(f"{API_URL}/users", params=params)
        return response.json()
    except Exception as e:
        st.error(f"Error fetching users: {e}")
        return []

@st.cache_data(ttl=60)
def fetch_leaderboard(period="week", limit=10):
    try:
        response = requests.get(f"{API_URL}/leaderboard", params={"period": period, "limit": limit})
        return response.json()
    except Exception as e:
        st.error(f"Error fetching leaderboard: {e}")
        return []

def fetch_weekly_activity():
    try:
        response = requests.get(f"{API_URL}/activity/weekly")
        return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"Error fetching weekly activity: {e}")
        return pd.DataFrame()

def send_announcement(message, message_type, target_audience, pin_message, notify_all):
    try:
        data = {
            "message": message,
            "message_type": message_type,
            "target_audience": target_audience,
            "pin_message": pin_message,
            "notify_all": notify_all
        }
        response = requests.post(f"{API_URL}/announcements", json=data, params={"admin_id": 1})
        return response.json()
    except Exception as e:
        st.error(f"Error sending announcement: {e}")
        return None

def update_user_status(user_id, status):
    try:
        response = requests.put(f"{API_URL}/users/{user_id}/status", params={"status": status})
        return response.json()
    except Exception as e:
        st.error(f"Error updating user: {e}")
        return None

# =============================================================================
# SIDEBAR
# =============================================================================

st.sidebar.title("Mutolaa Admin")
page = st.sidebar.radio("Navigation", ["📊 Dashboard", "👥 Users", "📢 Announcements", "⚙️ Settings"])

# =============================================================================
# PAGE: DASHBOARD
# =============================================================================

if page == "📊 Dashboard":
    st.markdown('<p class="main-header">📊 Dashboard</p>', unsafe_allow_html=True)
    stats = fetch_stats()

    if stats:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("👥 Total Users", f"{stats['total_users']:,}", f"+{stats['weekly_growth']:.1f}% this week")

        with col2:
            if stats['total_users'] > 0:
                active_percent = (stats['active_today'] / stats['total_users']) * 100
                delta_text = f"{active_percent:.1f}% of total"
            else:
                delta_text = "0% (no users yet)"
            st.metric("✅ Active Today", f"{stats['active_today']:,}", delta_text)

        with col3:
            st.metric("📖 Total Pages", f"{stats['total_pages']:,}", f"Avg {stats['avg_pages_per_day']:.0f}/day")

        with col4:
            st.metric("📚 Books Completed", f"{stats['books_completed']:,}", "This month")

        st.markdown("---")

        # Weekly Activity Chart
        st.subheader("📈 Weekly Activity")
        weekly_data = fetch_weekly_activity()
        if not weekly_data.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=weekly_data['Day'], y=weekly_data['Pages'], name='Pages Read'))
            fig.add_trace(go.Scatter(x=weekly_data['Day'], y=weekly_data['Users'], name='Active Users', yaxis='y2'))
            fig.update_layout(yaxis=dict(title='Pages'), yaxis2=dict(title='Users', overlaying='y', side='right'))
            st.plotly_chart(fig, use_container_width=True)

        # Leaderboard
        st.subheader("🏆 Top Readers This Week")
        leaderboard = fetch_leaderboard(period="week", limit=10)
        if leaderboard:
            df_leaderboard = pd.DataFrame(leaderboard)
            df_leaderboard['Medal'] = df_leaderboard['rank'].apply(
                lambda x: '🥇' if x == 1 else '🥈' if x == 2 else '🥉' if x == 3 else ''
            )
            # ensure 'books' column exists
            if 'books' not in df_leaderboard.columns:
                df_leaderboard['books'] = 0
            df_leaderboard = df_leaderboard[['Medal', 'rank', 'name', 'pages', 'books']]
            df_leaderboard.columns = ['', 'Rank', 'Name', 'Pages', 'Books']
            st.dataframe(df_leaderboard, use_container_width=True, hide_index=True)

# =============================================================================
# PAGE: USERS
# =============================================================================

elif page == "👥 Users":
    st.markdown('<p class="main-header">👥 User Management</p>', unsafe_allow_html=True)
    users = fetch_users()
    if users:
        for user in users:
            with st.expander(f"👤 {user['first_name']} (@{user.get('username','N/A')}) - {user['total_pages']} pages"):
                st.write(f"ID: {user['id']} | Telegram: {user['telegram_id']} | Status: {user['status']}")
                new_status = st.selectbox("Change Status", ["active","admin","banned"], key=f"status_{user['id']}")
                if st.button("💾 Update", key=f"update_{user['id']}"):
                    update_user_status(user['id'], new_status)
                    st.success("✅ Status updated!")

# =============================================================================
# PAGE: ANNOUNCEMENTS
# =============================================================================

elif page == "📢 Announcements":
    st.markdown('<p class="main-header">📢 Announcements</p>', unsafe_allow_html=True)
    message = st.text_area("Message")
    if st.button("📤 Send Announcement"):
        send_announcement(message, "general", "all", False, True)   
        st.success("✅ Announcement sent!")

    st.subheader("📜 Recent Announcements")
    announcements = requests.get(f"{API_URL}/announcements").json()
    for ann in announcements:
        try:
            created = datetime.fromisoformat(ann['created_at']).strftime("%Y-%m-%d")
        except Exception:
            created = ann['created_at'][:10]
        st.write(f"📅 {created} - {ann['message']}")

# =============================================================================
# PAGE: SETTINGS
# =============================================================================

elif page == "⚙️ Settings":
    st.markdown('<p class="main-header">⚙️ Bot Settings</p>', unsafe_allow_html=True)
    st.write("Settings management coming soon...")
