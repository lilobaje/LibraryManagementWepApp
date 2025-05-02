# In your forms.py

from django import forms
from django.contrib.auth.models import User
from . import models
from .models import Book, Student # Import Book and Student explicitly
from django.core.validators import RegexValidator

class IssueBookForm(forms.Form):
    # Updated to select the Book object directly using ModelChoiceField
    # The queryset now filters for books that have available copies
    book = forms.ModelChoiceField(
        queryset=Book.objects.filter(available_quantity__gt=0),
        empty_label="Select Book",
        label="Book"
    )
    # This seems fine, selecting the Student object by its ID (primary key)
    student = forms.ModelChoiceField(
        queryset=models.Student.objects.all(),
        empty_label="Select Student",
        label="Student Details"
    )

    # Apply CSS classes to the widgets
    book.widget.attrs.update({'class': 'form-control'})
    student.widget.attrs.update({'class':'form-control'})

    # Optional: You might want to add fields for issued_date or expiry_date
    # if you want the admin to be able to set these manually sometimes,
    # although your model provides defaults.
    # issued_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)
    # expiry_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)

    from django import forms
from django.core.validators import RegexValidator

class StudentForm(forms.Form):
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'First Name',
        })
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Last Name',
        })
    )
    username = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Username',
            'id': 'id_username'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Email',
            'id': 'id_email'
        })
    )
    phone = forms.CharField(
        validators=[RegexValidator(r'^\d{10,15}$')],
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Mobile Number',
        })
    )
    branch = forms.ChoiceField(
        choices=[
            ("", "Select Branch"),
            ("Junior secondary", "Junior Secondary School"),
            ("Senior Secondary", "Senior Secondary School")
        ],
        widget=forms.Select(attrs={
            'class': 'form-control form-control-lg'
        })
    )
    classroom = forms.ChoiceField(
        choices=[
            ("", "Select Class"),
            ("jss1", "JSS1"),
            ("jss2", "JSS2"),
            ("jss3", "JSS3"),
            ("ss1", "SS1"),
            ("ss2", "SS2"),
            ("ss3", "SS3")
        ],
        widget=forms.Select(attrs={
            'class': 'form-control form-control-lg'
        })
    )
    image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control form-control-lg'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Password'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Confirm Password'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match")
