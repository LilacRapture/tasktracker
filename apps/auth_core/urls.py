from django.urls import path

from .views import LoginView, LogoutView, RegisterView, TokenRefreshView, WsTicketView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("ws-ticket/", WsTicketView.as_view(), name="auth-ws-ticket"),
]
