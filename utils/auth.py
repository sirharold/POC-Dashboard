"""
Simple authentication module for the dashboard.
"""
import streamlit as st
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

def login_form():
    """Display login form and handle authentication."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
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
                    st.success("✅ ¡Acceso autorizado!")
                    st.rerun()
                else:
                    st.error("❌ Email o contraseña incorrectos")
        
        # Help section
        with st.expander("💡 Información de acceso"):
            st.markdown("""
            **Usuarios de prueba:**
            - **Email:** admin@dashboardepmaps.com  
              **Password:** AdminPass123
            
            - **Email:** user@dashboardepmaps.com  
              **Password:** UserPass123
            
            **Requisitos de contraseña:**
            - Mínimo 8 caracteres
            - Al menos 1 mayúscula, 1 minúscula, 1 número
            """)
        
        return False
    
    return True

def logout():
    """Handle user logout."""
    st.session_state.authenticated = False
    if "username" in st.session_state:
        del st.session_state.username
    if "user_name" in st.session_state:
        del st.session_state.user_name
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