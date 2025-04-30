# In your forms.py

from django import forms
from django.contrib.auth.models import User
from . import models
from .models import Book, Student # Import Book and Student explicitly

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