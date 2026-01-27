from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Sum, Count, F
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from django.views.generic import ListView
from django.urls import reverse_lazy

from .models import Account, Liability
from .forms import LiabilityForm


def home(request):
    """
    Home page view - displays different content for authenticated vs anonymous users
    """
    return render(request, 'fin_manager/home.html', {'user': request.user})


def register(request):
    """
    User registration view
    """
    # Redirect if user is already logged in
    if request.user.is_authenticated:
        messages.info(request, 'You are already logged in.')
        return redirect('home')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            
            # Log the user in automatically after registration
            login(request, user)
            
            # Add success message
            messages.success(request, f'Welcome {username}! Your account has been created.')
            return redirect('home')
        else:
            # Add error message if form is invalid
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    """
    User login view
    """
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {username}!')
            
            # Redirect to 'next' parameter if it exists
            next_url = request.POST.get('next') or request.GET.get('next') or 'home'
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'registration/login.html')


def logout_view(request):
    """
    User logout view
    """
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


class ExpenseListView(LoginRequiredMixin, FormView):
    """
    View to display expense list and add new liabilities
    """
    template_name = 'expenses/expense_list.html'
    form_class = LiabilityForm
    success_url = reverse_lazy('expenses')  # Use reverse_lazy for class-based views
    login_url = '/login/'  # Redirect to login if not authenticated
    
    def form_valid(self, form):
        """
        Process valid form submission
        """
        try:
            # Get or create the user's account
            account, created = Account.objects.get_or_create(user=self.request.user)
            
            # Create a new liability instance
            liability = Liability(
                name=form.cleaned_data['name'],
                amount=form.cleaned_data['amount'],
                interest_rate=form.cleaned_data.get('interest_rate', 0),
                end_date=form.cleaned_data['end_date'],
                user=self.request.user
            )
            liability.save()
            
            # Link liability to account
            account.liability_list.add(liability)
            
            # Add success message
            messages.success(self.request, f'Liability "{liability.name}" added successfully!')
            
        except Exception as e:
            # Handle any errors
            messages.error(self.request, f'Error adding liability: {str(e)}')
            return self.form_invalid(form)
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """
        Handle invalid form submission
        """
        messages.error(self.request, 'Please correct the errors in the form.')
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """
        Add expense data to context
        """
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Retrieve user's accounts
        accounts = Account.objects.filter(user=user).prefetch_related('liability_list')
        
        # Create a dictionary to store expense data grouped by month
        expense_data = {}
        
        for account in accounts:
            liabilities = account.liability_list.all().order_by('-end_date')
            
            for liability in liabilities:
                # Group by year-month
                year_month = liability.end_date.strftime('%Y-%m')
                
                if year_month not in expense_data:
                    expense_data[year_month] = []
                
                expense_data[year_month].append({
                    'id': liability.id,
                    'name': liability.name,
                    'amount': liability.amount,
                    'interest_rate': liability.interest_rate,
                    'end_date': liability.end_date,
                })
        
        # Sort expense_data by year-month (most recent first)
        expense_data = dict(sorted(expense_data.items(), reverse=True))
        
        context['expense_data'] = expense_data
        context['total_liabilities'] = sum(
            liability['amount'] for liabilities in expense_data.values() 
            for liability in liabilities
        )
        
        return context


# Optional: Function-based view alternative for expenses
@login_required(login_url='/login/')
def expense_list_view(request):
    """
    Function-based view alternative for expense list
    """
    if request.method == 'POST':
        form = LiabilityForm(request.POST)
        if form.is_valid():
            try:
                # Get or create account
                account, _ = Account.objects.get_or_create(user=request.user)
                
                # Create liability
                liability = Liability(
                    name=form.cleaned_data['name'],
                    amount=form.cleaned_data['amount'],
                    interest_rate=form.cleaned_data.get('interest_rate', 0),
                    end_date=form.cleaned_data['end_date'],
                    user=request.user
                )
                liability.save()
                account.liability_list.add(liability)
                
                messages.success(request, f'Liability "{liability.name}" added successfully!')
                return redirect('expenses')
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = LiabilityForm()
    
    # Get expense data
    accounts = Account.objects.filter(user=request.user).prefetch_related('liability_list')
    expense_data = {}
    
    for account in accounts:
        liabilities = account.liability_list.all().order_by('-end_date')
        for liability in liabilities:
            year_month = liability.end_date.strftime('%Y-%m')
            if year_month not in expense_data:
                expense_data[year_month] = []
            
            expense_data[year_month].append({
                'id': liability.id,
                'name': liability.name,
                'amount': liability.amount,
                'interest_rate': liability.interest_rate,
                'end_date': liability.end_date,
            })
    
    # Sort by date
    expense_data = dict(sorted(expense_data.items(), reverse=True))
    
    context = {
        'form': form,
        'expense_data': expense_data,
        'total_liabilities': sum(
            liability['amount'] for liabilities in expense_data.values() 
            for liability in liabilities
        )
    }
    
    return render(request, 'expenses/expense_list.html', context)