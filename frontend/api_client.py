import os
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

class APIClient:
    @staticmethod
    def get_headers(auth_required=True):
        headers = {}
        if auth_required and st.session_state.get("access_token"):
            headers["Authorization"] = f"Bearer {st.session_state['access_token']}"
        return headers

    @staticmethod
    def handle_response(response, method, url, auth_required, **kwargs):
        # If access token has expired (401), try to auto-refresh
        if response.status_code == 401 and auth_required and st.session_state.get("refresh_token"):
            if APIClient.refresh_tokens():
                # Retry original request with new token
                headers = APIClient.get_headers(auth_required=True)
                if "headers" in kwargs:
                    kwargs["headers"].update(headers)
                else:
                    kwargs["headers"] = headers
                
                retry_resp = requests.request(method, url, **kwargs)
                return retry_resp
            else:
                # Refresh failed - clear session state and log out user
                st.session_state["access_token"] = None
                st.session_state["refresh_token"] = None
                st.session_state["user_role"] = None
                st.session_state["username"] = None
                st.session_state["last_activity"] = None
                st.toast("Session expired. Please log in again.", icon="⚠️")
                st.rerun()
                
        return response

    @staticmethod
    def refresh_tokens():
        refresh_url = f"{BACKEND_URL}/api/auth/refresh"
        refresh_token = st.session_state.get("refresh_token")
        if not refresh_token:
            return False
            
        try:
            resp = requests.post(refresh_url, json={"refresh_token": refresh_token})
            if resp.status_code == 200:
                data = resp.json()
                st.session_state["access_token"] = data["access_token"]
                st.session_state["refresh_token"] = data["refresh_token"]
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def get(endpoint, auth_required=True, params=None):
        url = f"{BACKEND_URL}{endpoint}"
        headers = APIClient.get_headers(auth_required)
        try:
            resp = requests.get(url, headers=headers, params=params)
            return APIClient.handle_response(resp, "GET", url, auth_required, params=params)
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend service. Ensure FastAPI is running.")
            return None

    @staticmethod
    def post(endpoint, auth_required=True, json=None, data=None, files=None):
        url = f"{BACKEND_URL}{endpoint}"
        headers = APIClient.get_headers(auth_required)
        try:
            resp = requests.post(url, headers=headers, json=json, data=data, files=files)
            return APIClient.handle_response(resp, "POST", url, auth_required, json=json, data=data, files=files)
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend service. Ensure FastAPI is running.")
            return None

    @staticmethod
    def put(endpoint, auth_required=True, json=None):
        url = f"{BACKEND_URL}{endpoint}"
        headers = APIClient.get_headers(auth_required)
        try:
            resp = requests.put(url, headers=headers, json=json)
            return APIClient.handle_response(resp, "PUT", url, auth_required, json=json)
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend service. Ensure FastAPI is running.")
            return None
