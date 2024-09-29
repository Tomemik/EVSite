from django.urls import path

from . import views

urlpatterns = [
    path("", views.UserDetailsView.as_view(), name="user_view"),
    path("login/", views.LoginView.as_view(), name="knox_login"),
    path("logout/", views.LogoutView.as_view(), name="knox_logout"),
    path("register/", views.UserRegisterView.as_view(), name="register_user"),
]
