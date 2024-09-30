from django.urls import path

from knox import views as knox_views
from . import views

urlpatterns = [
    path("", views.UserDetailsView.as_view(), name="user_view"),
    path("login/", views.LoginView.as_view(), name="knox_login"),
    path("logout/", knox_views.LogoutView.as_view(), name="knox_logout"),
    path("register/", views.UserRegisterView.as_view(), name="register_user"),
]