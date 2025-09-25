"""
Simple authentication module for the dashboard.
"""
import streamlit as st
import streamlit.components.v1
import hashlib

# Simple user database (in production, use proper database)
USERS = {
    "admin@dashboardepmaps.com": {
        "name": "Admin",
        "password": "790f48e3ba51e2d0762e7d4a74d4076a62cfb34d44e3dfbc43798fe9ff399602"  # AdminPass123
    },
    "user@dashboardepmaps.com": {
        "name": "User", 
        "password": "8e3bde512bf178d26128fdcda19de3ecea6ce26c4edaa177a5e2d49713272443"  # UserPass123
    }
}

def hash_password(password: str) -> str:
    """Hash password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return hash_password(password) == hashed

def authenticate_user(username: str, password: str) -> bool:
    """Authenticate user credentials."""
    if username in USERS:
        return verify_password(password, USERS[username]["password"])
    return False

def get_user_name(username: str) -> str:
    """Get user display name."""
    return USERS.get(username, {}).get("name", "Unknown")

def check_stored_auth():
    """Check for stored authentication and restore session if valid."""
    if "auth_checked" not in st.session_state:
        st.session_state.auth_checked = True
        
        # JavaScript to check localStorage and restore session
        auth_check_script = """
        <script>
        function checkStoredAuth() {
            const authData = localStorage.getItem('dashboard_epmaps_auth');
            if (authData) {
                try {
                    const auth = JSON.parse(authData);
                    const now = new Date().getTime();
                    if (now < auth.expires && auth.authenticated === true) {
                        // Send auth data to Streamlit
                        window.parent.postMessage({
                            type: 'streamlit:setComponentValue',
                            key: 'restore_auth',
                            value: {
                                authenticated: true,
                                username: auth.username,
                                user_name: auth.user_name,
                                expires: auth.expires
                            }
                        }, '*');
                        return true;
                    } else {
                        localStorage.removeItem('dashboard_epmaps_auth');
                    }
                } catch (e) {
                    localStorage.removeItem('dashboard_epmaps_auth');
                }
            }
            return false;
        }
        
        // Check immediately
        checkStoredAuth();
        </script>
        """
        
        st.components.v1.html(auth_check_script, height=0)
        
        # Check if authentication was restored from storage
        if 'restore_auth' in st.session_state:
            auth_data = st.session_state.restore_auth
            if auth_data.get('authenticated'):
                st.session_state.authenticated = True
                st.session_state.username = auth_data.get('username', '')
                st.session_state.user_name = auth_data.get('user_name', '')
                del st.session_state.restore_auth
                st.rerun()

def login_form():
    """Display login form and handle authentication."""
    # Initialize authentication state
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    # Check for stored authentication first
    if not st.session_state.authenticated:
        check_stored_auth()
    
    if not st.session_state.authenticated:
        st.markdown("# 🔐 Dashboard EPMAPS - Login")
        st.markdown("---")
        
        with st.form("login_form"):
            st.markdown("### Acceder al Dashboard")
            username = st.text_input("📧 Email", placeholder="usuario@email.com")
            password = st.text_input("🔒 Contraseña", type="password", placeholder="Tu contraseña")
            submit = st.form_submit_button("🚀 Iniciar Sesión", use_container_width=True)
            
            if submit:
                if authenticate_user(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.user_name = get_user_name(username)
                    
                    # Store authentication in browser localStorage (24 hours)
                    store_auth_script = f"""
                    <script>
                    const authData = {{
                        authenticated: true,
                        username: '{username}',
                        user_name: '{get_user_name(username)}',
                        expires: new Date().getTime() + (24 * 60 * 60 * 1000),
                        timestamp: new Date().getTime()
                    }};
                    localStorage.setItem('dashboard_epmaps_auth', JSON.stringify(authData));
                    console.log('Authentication stored successfully');
                    </script>
                    """
                    st.components.v1.html(store_auth_script, height=0)
                    
                    st.success("✅ ¡Acceso autorizado!")
                    st.rerun()
                else:
                    st.error("❌ Email o contraseña incorrectos")
        
        return False
    
    return True

def logout():
    """Handle user logout."""
    st.session_state.authenticated = False
    if "username" in st.session_state:
        del st.session_state.username
    if "user_name" in st.session_state:
        del st.session_state.user_name
    if "auth_checked" in st.session_state:
        del st.session_state.auth_checked
    
    # Clear authentication from browser localStorage
    clear_auth_script = """
    <script>
    localStorage.removeItem('dashboard_epmaps_auth');
    console.log('Authentication cleared from storage');
    </script>
    """
    st.components.v1.html(clear_auth_script, height=0)
    
    st.rerun()

def add_user_header():
    """Add user info and logout button to the main header."""
    if st.session_state.get("authenticated", False):
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            # Detect current page and show appropriate title
            if 'alarm_report' in st.query_params:
                st.markdown("# ☁️ Dashboard EPMAPS - 📊 Reporte de Alarmas")
            elif 'poc_vm_id' in st.query_params:
                st.markdown("# ☁️ Dashboard EPMAPS - Detalle VM")
            else:
                st.markdown("# ☁️ Dashboard EPMAPS")
        
        with col2:
            st.markdown(f"<div style='text-align: right; padding-top: 10px;'>"
                       f"👤 **{st.session_state.get('user_name', 'Usuario')}**<br>"
                       f"📧 {st.session_state.get('username', '')}</div>", 
                       unsafe_allow_html=True)
        
        with col3:
            if st.button("🚪 Cerrar Sesión", use_container_width=True):
                logout()

def add_logout_button():
    """Add logout button to sidebar (legacy function - kept for compatibility)."""
    if st.session_state.get("authenticated", False):
        with st.sidebar:
            st.markdown("---")
            st.markdown(f"👤 **{st.session_state.get('user_name', 'Usuario')}**")
            st.markdown(f"📧 {st.session_state.get('username', '')}")
            if st.button("🚪 Cerrar Sesión", use_container_width=True):
                logout()