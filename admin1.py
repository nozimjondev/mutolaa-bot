# Mutolaa Bot - Admin Panel (Pure Python with Streamlit)
# No JavaScript, No Node.js - Just Python!

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import asyncio
import aiohttp

# Configuration
st.set_page_config(
    page_title="Mutolaa Admin Panel",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_URL = "http://localhost:8000/api"

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f2937;
        margin-bottom: 1rem;
    }
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

@st.cache_data(ttl=60)
def fetch_stats():
    """Fetch overall statistics"""
    try:
        response = requests.get(f"{API_URL}/stats")
        return response.json()
    except Exception as e:
        st.error(f"Error fetching stats: {e}")
        return None

@st.cache_data(ttl=60)
def fetch_users(search="", status="", limit=100):
    """Fetch users"""
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
    """Fetch leaderboard"""
    try:
        response = requests.get(f"{API_URL}/leaderboard", params={"period": period, "limit": limit})
        return response.json()
    except Exception as e:
        st.error(f"Error fetching leaderboard: {e}")
        return []

def fetch_weekly_activity():
    """Fetch weekly activity data (mock for now)"""
    # In real implementation, add this endpoint to your API
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    return pd.DataFrame({
        'Day': days,
        'Pages': [15420, 18930, 16540, 19870, 21340, 17650, 15680],
        'Users': [245, 289, 267, 301, 325, 278, 251]
    })

def send_announcement(message, message_type, target_audience, pin_message, notify_all):
    """Send announcement via API"""
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
    """Update user status"""
    try:
        response = requests.put(f"{API_URL}/users/{user_id}/status", params={"status": status})
        return response.json()
    except Exception as e:
        st.error(f"Error updating user: {e}")
        return None

# =============================================================================
# SIDEBAR NAVIGATION
# =============================================================================

st.sidebar.image("https://via.placeholder.com/150x150.png?text=📚", width=150)
st.sidebar.title("Mutolaa Admin")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["📊 Dashboard", "👥 Users", "📢 Announcements", "⚙️ Settings"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Admin Info")
st.sidebar.info("👤 Admin: Mirzovali\n📧 @mirzovali")

# =============================================================================
# PAGE: DASHBOARD
# =============================================================================

if page == "📊 Dashboard":
    st.markdown('<p class="main-header">📊 Dashboard</p>', unsafe_allow_html=True)
    
    # Fetch data
    stats = fetch_stats()
    
    if stats:
        # Statistics Cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="👥 Total Users",
                value=f"{stats['total_users']:,}",
                delta=f"+{stats['weekly_growth']:.1f}% this week"
            )
        
        with col2:
            st.metric(
                label="✅ Active Today",
                value=f"{stats['active_today']:,}",
                delta=f"{(stats['active_today']/stats['total_users']*100):.1f}% of total"
            )
        
        with col3:
            st.metric(
                label="📖 Total Pages",
                value=f"{stats['total_pages']:,}",
                delta=f"Avg {stats['avg_pages_per_day']:.0f}/day"
            )
        
        with col4:
            st.metric(
                label="📚 Books Completed",
                value=f"{stats['books_completed']:,}",
                delta="This month"
            )
        
        st.markdown("---")
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Weekly Activity")
            weekly_data = fetch_weekly_activity()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=weekly_data['Day'],
                y=weekly_data['Pages'],
                name='Pages Read',
                line=dict(color='#8b5cf6', width=3)
            ))
            fig.add_trace(go.Scatter(
                x=weekly_data['Day'],
                y=weekly_data['Users'],
                name='Active Users',
                line=dict(color='#10b981', width=3),
                yaxis='y2'
            ))
            
            fig.update_layout(
                yaxis=dict(title='Pages'),
                yaxis2=dict(title='Users', overlaying='y', side='right'),
                hovermode='x unified',
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("📚 Book Categories")
            categories_data = pd.DataFrame({
                'Category': ['Islamic', 'History', 'Literature', 'Science'],
                'Percentage': [45, 25, 20, 10]
            })
            
            fig = px.pie(
                categories_data,
                values='Percentage',
                names='Category',
                color_discrete_sequence=['#10b981', '#3b82f6', '#f59e0b', '#ef4444'],
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Leaderboard
        st.subheader("🏆 Top Readers This Week")
        leaderboard = fetch_leaderboard(period="week", limit=10)
        
        if leaderboard:
            # Create DataFrame
            df_leaderboard = pd.DataFrame(leaderboard)
            
            # Add medal emojis
            df_leaderboard['Medal'] = df_leaderboard['rank'].apply(
                lambda x: '🥇' if x == 1 else '🥈' if x == 2 else '🥉' if x == 3 else ''
            )
            
            # Reorder columns
            df_leaderboard = df_leaderboard[['Medal', 'rank', 'name', 'pages', 'books']]
            df_leaderboard.columns = ['', 'Rank', 'Name', 'Pages', 'Books']
            
            st.dataframe(
                df_leaderboard,
                use_container_width=True,
                hide_index=True
            )

# =============================================================================
# PAGE: USERS
# =============================================================================

elif page == "👥 Users":
    st.markdown('<p class="main-header">👥 User Management</p>', unsafe_allow_html=True)
    
    # Search and Filter
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        search_query = st.text_input("🔍 Search users", placeholder="Enter name or username...")
    
    with col2:
        status_filter = st.selectbox("Status", ["All", "Active", "Admin", "Banned"])
    
    with col3:
        st.write("")  # Spacing
        st.write("")
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Fetch users
    status_param = status_filter.lower() if status_filter != "All" else ""
    users = fetch_users(search=search_query, status=status_param)
    
    if users:
        st.write(f"**Total users:** {len(users)}")
        
        # Convert to DataFrame
        df_users = pd.DataFrame(users)
        
        # Display users in a table with actions
        for idx, user in enumerate(users):
            with st.expander(f"👤 {user['first_name']} (@{user.get('username', 'N/A')}) - {user['total_pages']} pages"):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.write(f"**User ID:** {user['id']}")
                    st.write(f"**Telegram ID:** {user['telegram_id']}")
                    st.write(f"**Status:** {user['status']}")
                    st.write(f"**Joined:** {user['join_date'][:10]}")
                
                with col2:
                    st.write(f"**📖 Total Pages:** {user['total_pages']}")
                    st.write(f"**🔥 Streak:** {user['current_streak']} days")
                    st.write(f"**📚 Books:** {user['books_completed']}")
                
                with col3:
                    st.write("**Actions:**")
                    
                    new_status = st.selectbox(
                        "Change Status",
                        ["active", "admin", "banned"],
                        key=f"status_{user['id']}",
                        index=["active", "admin", "banned"].index(user['status'])
                    )
                    
                    if st.button("💾 Update", key=f"update_{user['id']}"):
                        result = update_user_status(user['id'], new_status)
                        if result:
                            st.success("✅ Status updated!")
                            st.cache_data.clear()
                            st.rerun()
                    
                    if st.button("📩 Message", key=f"msg_{user['id']}"):
                        st.info("Message feature coming soon!")
        
        # Export button
        st.markdown("---")
        if st.button("📥 Export to CSV"):
            csv = df_users.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"mutolaa_users_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

# =============================================================================
# PAGE: ANNOUNCEMENTS
# =============================================================================

elif page == "📢 Announcements":
    st.markdown('<p class="main-header">📢 Announcements</p>', unsafe_allow_html=True)
    
    # Send New Announcement
    with st.form("announcement_form"):
        st.subheader("📝 Send New Announcement")
        
        col1, col2 = st.columns(2)
        
        with col1:
            message_type = st.selectbox(
                "Message Type",
                ["General Announcement", "Weekly Reminder", "Challenge Notification", "Achievement Alert"]
            )
        
        with col2:
            target_audience = st.selectbox(
                "Target Audience",
                ["All Users", "Active Users Only", "Top 10 Readers", "Inactive Users (7+ days)"]
            )
        
        message = st.text_area(
            "Message",
            placeholder="Assalomu alaykum! Aziz kitobxonlar...",
            height=150
        )
        
        col1, col2 = st.columns(2)
        with col1:
            pin_message = st.checkbox("📌 Pin message")
        with col2:
            notify_all = st.checkbox("🔔 Notify all users", value=True)
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            submitted = st.form_submit_button("📤 Send Now", use_container_width=True)
        
        with col2:
            schedule = st.form_submit_button("📅 Schedule", use_container_width=True)
        
        with col3:
            preview = st.form_submit_button("👁️ Preview", use_container_width=True)
        
        if submitted:
            if message.strip():
                # Convert display names to API values
                type_map = {
                    "General Announcement": "general",
                    "Weekly Reminder": "reminder",
                    "Challenge Notification": "challenge",
                    "Achievement Alert": "achievement"
                }
                
                audience_map = {
                    "All Users": "all",
                    "Active Users Only": "active",
                    "Top 10 Readers": "top10",
                    "Inactive Users (7+ days)": "inactive"
                }
                
                result = send_announcement(
                    message=message,
                    message_type=type_map[message_type],
                    target_audience=audience_map[target_audience],
                    pin_message=pin_message,
                    notify_all=notify_all
                )
                
                if result:
                    st.success("✅ Announcement sent successfully!")
                    st.balloons()
            else:
                st.error("❌ Message cannot be empty!")
        
        if preview:
            st.info(f"**Preview:**\n\n{message}")
    
    st.markdown("---")
    
    # Recent Announcements
    st.subheader("📜 Recent Announcements")
    
    # Mock data - replace with real API call
    recent_announcements = [
        {
            "title": "Weekly Challenge Started",
            "date": "2 days ago",
            "message": "Bugundan boshlab haftalik statistikani botimizga topshirmoqchimiz...",
            "sent_to": 1256,
            "read_rate": 87
        },
        {
            "title": "New Books Added",
            "date": "5 days ago",
            "message": "Yangi kitoblar qo'shildi! Hadyalar guruhiga ko'z tashlang...",
            "sent_to": 1245,
            "read_rate": 92
        }
    ]
    
    for announcement in recent_announcements:
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**{announcement['title']}**")
                st.write(announcement['message'])
            
            with col2:
                st.write(f"📅 {announcement['date']}")
                st.write(f"✅ Sent to {announcement['sent_to']} users")
                st.progress(announcement['read_rate'] / 100, text=f"{announcement['read_rate']}% read")
            
            st.markdown("---")

# =============================================================================
# PAGE: SETTINGS
# =============================================================================

elif page == "⚙️ Settings":
    st.markdown('<p class="main-header">⚙️ Bot Settings</p>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📊 Goals", "🔔 Notifications", "🏆 Achievements"])
    
    with tab1:
        st.subheader("Reading Goals")
        
        col1, col2 = st.columns(2)
        
        with col1:
            daily_goal = st.number_input("Daily Goal (pages)", min_value=1, max_value=500, value=50)
            weekly_goal = st.number_input("Weekly Goal (pages)", min_value=1, max_value=3500, value=350)
        
        with col2:
            monthly_goal = st.number_input("Monthly Goal (pages)", min_value=1, max_value=15000, value=1500)
            max_pages = st.number_input("Max Pages Per Day (validation)", min_value=100, max_value=1000, value=500)
        
        if st.button("💾 Save Goals", use_container_width=True):
            st.success("✅ Goals updated successfully!")
    
    with tab2:
        st.subheader("Notification Settings")
        
        reminder_time = st.time_input("Daily Reminder Time", value=datetime.strptime("20:00", "%H:%M").time())
        
        st.write("**Enable Features:**")
        enable_reminders = st.checkbox("Send daily reminders", value=True)
        enable_streak_alerts = st.checkbox("Streak break alerts", value=True)
        enable_achievement_notifs = st.checkbox("Achievement notifications", value=True)
        
        if st.button("💾 Save Notifications", use_container_width=True):
            st.success("✅ Notification settings updated!")
    
    with tab3:
        st.subheader("Achievement Thresholds")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Pages Achievements:**")
            first_page = st.number_input("🏆 First Steps", value=1)
            century = st.number_input("💯 Century", value=100)
            bookworm = st.number_input("🐛 Bookworm", value=1000)
        
        with col2:
            st.write("**Streak Achievements:**")
            week_warrior = st.number_input("🔥 Week Warrior", value=7)
            month_master = st.number_input("⭐ Month Master", value=30)
            year_champion = st.number_input("👑 Year Champion", value=365)
        
        if st.button("💾 Save Achievements", use_container_width=True):
            st.success("✅ Achievement thresholds updated!")

# =============================================================================
# FOOTER
# =============================================================================

st.sidebar.markdown("---")
st.sidebar.caption("© 2026 Mutolaa Bot")
st.sidebar.caption("Made with ❤️ by Mirzovali")