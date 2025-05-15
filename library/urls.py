# In your urls.py

from django.urls import path, include # Make sure to import include
from . import views, admin_views , student_views

urlpatterns = [
    path("", views.index, name="index"),

    # URLs for Django's built-in authentication views, including password reset
    path('accounts/', include('django.contrib.auth.urls')),

    # URLs for Book Management
    path("add_book/", views.add_book, name="add_book"),
    path("view_books/", views.view_books, name="view_books"),
    path("overdue_books_report/", views.overdue_books_report, name="overdue_books_report"),
    path("available_books_report/", views.available_books_report, name="available_books_report"),
    path('admin_view_holds/', views.admin_view_holds, name='admin_view_holds'), # Added URL for admin to view all holds
    # Added URL for book_detail
    path("book/<int:book_id>/", views.book_detail, name="book_detail"),
    path("edit_book/<int:book_id>/", views.edit_book, name="edit_book"),
    path("edit_book_save/", views.edit_book_save, name="edit_book_save"),
    path("delete_book/<int:myid>/", views.delete_book, name="delete_book"),
    path('Search_book/',views.Search_book,name='Search_book'),
    path('Search_student/', views.Search_student, name='Search_student'),

    # URLs for Student Management
    path("view_students/", views.view_students, name="view_students"),
    path("delete_student/<int:myid>/", views.delete_student, name="delete_student"),
    path('Search_book_admin/',views.Search_book_admin,name='Search_book_admin'),

    # URLs for Issued Books and Circulation
    path("issue_book/", views.issue_book, name="issue_book"),
    path("view_issued_book/", views.view_issued_book, name="view_issued_book"),
    path("delete_issued/<int:id>/", views.delete_issued, name="delete_issued"),
    path('returned/<int:pk>/', views.returned, name="returned"),
    path('not_returned/<int:id>/', views.not_returned, name="not_returned"),

    # URLs for Hold System
    path('book/<int:book_id>/place_hold/', views.place_hold, name='place_hold'),
    path('my_holds/', views.my_holds, name='my_holds'), # Added URL for viewing holds
    # Added URL for canceling holds
    path('cancel_hold/<int:hold_id>/', views.cancel_hold, name='cancel_hold'),

    path('student/dashboard/', views.student_dash, name='student_dash'),
    # URLs for Student Profile and Authentication
    path("student_issued_books/", views.student_issued_books, name="student_issued_books"),
    path("profile/", views.profile, name="profile"),
    path("edit_student_profile/", views.edit_student_profile, name="edit_student_profile"),
    # Note: Django's auth.urls includes a password change view at /accounts/password_change/
    # You might want to remove or rename your custom 'change_password' view if you use the built-in one.
    path("change_password/", views.change_password, name="change_password"),
    path("student_registration/", views.student_registration, name="student_registration"),
    # Note: Django's auth.urls includes a login view at /accounts/login/
    # You might want to remove or rename your custom 'student_login' and 'admin_login' views if you use the built-in one.
    path("student_login/", views.student_login, name="student_login"),
    path("admin_login/", views.admin_login, name="admin_login"),
    # Note: Django's auth.urls includes a logout view at /accounts/logout/
    # You might want to remove or rename your custom 'Logout' view if you use the built-in one.
    path("logout/", views.Logout, name="logout"),


    path("books/", views.book_list, name="book_list"), # Added URL for book_list

    # AJAX URLs
    path('check_email_exist/', views.check_email_exist, name="check_email_exist"),
    path('check_username_exist/', views.check_username_exist, name="check_username_exist"),

    # Dashboard
    path("dash/", views.dash, name="dash"),
]