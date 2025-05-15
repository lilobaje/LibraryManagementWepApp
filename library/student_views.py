from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.db.models import Q
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from . import forms
from .forms import StudentForm
# Import necessary models
from .models import Book, Student, IssuedBook, Hold, Genre, User


def index(request):
    # Display books on the index page
    books = Book.objects.all()
    return render(request, "index2.html", {"books": books})


# Helper function to check if a user is a student (based on having a related Student object)
def is_student(user):
    return hasattr(user, 'student')


@login_required(login_url='/student_login/')  # Redirect to student login if not logged in
def book_list(request):
    # Display books on the index page
    books = Book.objects.all()
    return render(request, "student/book_list.html", {"books": books})


@login_required(login_url='/student_login')
def Search_book(request):
    q = request.GET.get('q') if request.GET.get('q') is not None else ''
    # Searching by isbn, maybe add name, author, genre, etc.
    books = Book.objects.filter(
        Q(isbn__icontains=q) |
        Q(name__icontains=q) |
        Q(author__icontains=q) |
        Q(genres__name__icontains=q)  # Searching by genre name (requires distinct)
    ).distinct()  # Use distinct to avoid duplicate books if they have multiple matching genres
    context = {'books': books}
    return render(request, "student/book_list.html", context)


def book_detail(request, book_id):
    """ Displays the details of a specific book. """
    book = get_object_or_404(Book, id=book_id)

    # --- Add variable to check if the user is a student ---
    is_student_user = False
    if request.user.is_authenticated:
        is_student_user = hasattr(request.user, 'student')
    # --- End added variable ---

    # Fetch active holds for this book if you want to display the queue
    active_holds = Hold.objects.filter(book=book, is_active=True).order_by('place_date')

    # Determine if the logged-in user has an active hold on this book
    user_has_hold = False
    if request.user.is_authenticated and is_student_user:  # Use the new variable here too
        user_has_hold = Hold.objects.filter(book=book, student=request.user.student, is_active=True).exists()

    context = {
        'book': book,
        'active_holds': active_holds,
        'user_has_hold': user_has_hold,
        'is_student_user': is_student_user,  # <-- Pass the new variable to the template
    }
    return render(request, 'book_detail.html', context)


@login_required(login_url='/student_login')
def place_hold(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    user = request.user

    # Ensure the user is a student
    if not hasattr(user, 'student'):
        messages.error(request, "Only students can place holds.")
        # You might want to redirect to student login or the index page if not a student
        return redirect('book_detail', book_id=book.id)
    student = user.student

    # --- Add checks before placing the hold ---

    # Check if the book is available (no need for a hold if available)
    if book.available_quantity > 0:
        messages.info(request, f"Book '{book.name}' is currently available. No need to place a hold.")
        return redirect('book_detail', book_id=book.id)

    # Check if the student already has an active hold on this book
    existing_hold = Hold.objects.filter(book=book, student=student, is_active=True).exists()
    if existing_hold:
        messages.info(request, f"You already have an active hold on '{book.name}'.")
        return redirect('book_detail', book_id=book.id)

    # Optional: Check if the student currently has this book issued
    # You might not want them to place a hold if they already have a copy
    # current_issue = IssuedBook.objects.filter(book=book, student=student, book_status='Active').exists()
    # if current_issue:
    #     messages.info(request, f"You currently have '{book.name}' issued.")
    #     return redirect('book_detail', book_id=book.id)

    # If checks pass, create the hold
    Hold.objects.create(book=book, student=student, is_active=True)  # Ensure is_active is True by default
    messages.success(request, f"A hold has been placed on '{book.name}'.")

    return redirect('book_detail', book_id=book.id)


@login_required(login_url='/student_login')
def cancel_hold(request, hold_id):
    """ Allows a student to cancel their active hold. """
    user = request.user

    # Ensure the user is a student
    if not hasattr(user, 'student'):
        messages.error(request, "You do not have a student account.")
        return redirect('index')  # Redirect to a safe page

    student = user.student

    # Get the hold object or return 404 if it doesn't exist
    # Also ensure the hold belongs to the logged-in student and is active
    try:
        hold = Hold.objects.get(id=hold_id, student=student, is_active=True)
    except Hold.DoesNotExist:
        messages.error(request, "Hold not found or cannot be cancelled.")
        return redirect('my_holds')  # Redirect back to the My Holds page

    # --- Cancel the hold ---
    hold.is_active = False  # Mark the hold as inactive instead of deleting
    hold.save()
    # Alternatively, you could delete the hold: hold.delete()
    # Marking as inactive retains a history of holds placed.

    messages.success(request, f"Your hold on '{hold.book.name}' has been cancelled.")

    return redirect('my_holds')  # Redirect back to the My Holds page


@login_required(login_url='/student_login')
def my_holds(request):
    """ Displays the active holds for the logged-in student. """
    user = request.user

    # Ensure the user is a student
    if not hasattr(user, 'student'):
        messages.error(request, "You do not have a student account.")
        return redirect('index')  # Redirect to a safe page

    student = user.student

    # Get all active holds for this student, ordered by the date they were placed
    active_holds = Hold.objects.filter(student=student, is_active=True).order_by('place_date')

    context = {
        'active_holds': active_holds
    }
    return render(request, 'student/my_holds.html', context)  # We will create/update this template


@login_required(login_url='/student_login')
def student_issued_books(request):
    """ View for students to see their issued books. """
    # Get the student object for the logged-in user
    try:
        student = request.user.student
    except Student.DoesNotExist:
        messages.error(request, "User is not a student.")
        return redirect('index')  # Redirect to a safe page

    # Get issued books for this student, optimizing queries
    issued_books = IssuedBook.objects.filter(student=student).select_related('book')

    # The complex loop to build 'li1' is removed, you can access related objects directly in the template
    return render(request, 'student/books.html', {'issuedBooks': issued_books})


@login_required(login_url='/student_login')
def profile(request):
    # Fetch the student object for the logged-in user
    try:
        student = request.user.student
    except Student.DoesNotExist:
        messages.error(request, "User is not a student.")
        return redirect('index')  # Redirect to a safe page

    return render(request, "student/studentHome.html", {'student': student})


@login_required(login_url='/student_login')
def edit_profile(request):
    """ Allows students to edit their profile information. """
    try:
        student = request.user.student
    except Student.DoesNotExist:
        messages.error(request, "User is not a student.")
        return redirect('index')  # Redirect to a safe page

    if request.method == "POST":
        # Be cautious about which fields students can edit.
        # Avoid letting them change core User fields like username or email directly this way.
        # It's better to use Django Forms for validation and cleaner handling.

        # Updating User fields (handle with care or use a User Update Form)
        # request.user.email = request.POST.get('email') # Consider using EmailField in Student or User model
        # request.user.save()

        student.phone = request.POST.get('phone')
        student.branch = request.POST.get('branch')
        student.classroom = request.POST.get('classroom')
        student.adm_no = request.POST.get('roll_no')  # Mismatch with model field name 'adm_no' vs 'roll_no'
        # Handle image update
        if 'image' in request.FILES:
            student.image = request.FILES['image']

        try:
            student.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')  # Redirect back to the profile page
        except Exception as e:
            messages.error(request, f"Failed to update profile: {e}")
            # Redirect back to the edit page with current data
            return render(request, "student/edit.html", {'student': student})  # Pass student object

    # If GET request, display the current profile data in the form
    return render(request, "student/edit.html", {'student': student})


@login_required(login_url='/student_login')
def change_password(request):
    # This view seems fine for changing the logged-in user's password
    if request.method == "POST":
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')

        # Basic validation
        if not current_password or not new_password:
            messages.error(request, "Please fill in all fields.")
            return render(request, "student/changepsw.html")

        user = request.user  # Use request.user for the currently logged-in user

        if user.check_password(current_password):
            user.set_password(new_password)
            user.save()
            messages.success(request, "Password changed successfully!")
            # Consider logging the user out after password change for security
            # logout(request)
            # return redirect('login_url') # Redirect to login page
            return render(request, "student/changepsw.html")  # Or redirect to profile
        else:
            messages.error(request, "Incorrect current password.")
            return render(request, "student/changepsw.html")

    return render(request, "student/changepsw.html")


def student_registration(request):
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            password = data.get('password')
            confirm_password = data.get('confirm_password')

            if password != confirm_password:
                messages.error(request, "Passwords do not match.")
            elif User.objects.filter(username=data['username']).exists():
                messages.error(request, "Username already exists.")
            elif User.objects.filter(email=data['email']).exists():
                messages.error(request, "Email already exists.")
            else:
                user = User.objects.create_user(
                    username=data['username'],
                    email=data['email'],
                    password=password,
                    first_name=data['first_name'],
                    last_name=data['last_name']
                )

                # Create Student profile
                Student.objects.create(
                    user=user,
                    phone=data['phone'],
                    branch=data['branch'],
                    classroom=data['classroom'],
                    image=request.FILES.get('image')
                )

                messages.success(request, "Student registered successfully.")
                return redirect('student_login')  # ✅ Fixed redirect


@login_required(login_url='/student_login/') # Requires student login
def student_dash(request):
    """ Displays the dashboard for a logged-in student. """
    user = request.user

    # --- Check to ensure the logged-in user is a student ---
    if not hasattr(user, 'student'):
        messages.error(request, "You must be logged in as a student to access this page.")
        return redirect('index') # Redirect to index or student login if not a student
    # --- End of check ---

    student = user.student # Get the related Student object

    # Calculate counts specific to this student
    # Count active issued books for this student
    student_issued_books_count = IssuedBook.objects.filter(student=student, book_status='Active').count()

    # Count active holds for this student
    student_holds_count = Hold.objects.filter(student=student, is_active=True).count()

    context = {
        'student_issued_books_count': student_issued_books_count,
        'student_holds_count': student_holds_count,
        'student': student, # Pass the student object to the template
        'user': user, # Pass the user object as well
    }
    # We will create the student_dash.html template next
    return render(request, 'student/student_dashboard.html', context)
