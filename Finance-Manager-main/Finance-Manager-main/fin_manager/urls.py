from django.urls import path, include
from . import views

# App name for namespacing (optional but recommended)
app_name = 'fin_manager'

urlpatterns = [
    # Home page
    path('', views.home, name='home'),
    
    # Authentication URLs
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Expense management
    path('expenses/', views.ExpenseListView.as_view(), name='expenses'),
    
    # Optional: Django's built-in auth views for password reset
    # path('accounts/', include('django.contrib.auth.urls')),
]