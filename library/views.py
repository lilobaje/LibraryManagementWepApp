from library.forms import IssueBookForm
from django.shortcuts import redirect, render,HttpResponse
from django.http import HttpResponse, HttpResponseRedirect
from django.db.models import Q
from django.urls import reverse
from django.shortcuts import redirect, render
from .models import *
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from . import forms, models
from datetime import date
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib import messages

    
def index(request):
    books=Book.objects.all()
    return render(request, "index2.html" , {"books":books})

@login_required(login_url = '/admin_login')
def add_book(request):
    if request.method == "POST":
        name = request.POST['name']
        author = request.POST['author']
        isbn = request.POST['isbn']
        category = request.POST['category']
        image = request.FILES['image']
        description = request.POST['description']
        books = Book.objects.create(name=name, author=author, isbn=isbn, category=category, description=description, image=image)
        books.save()
        alert = True
        return render(request, "admin_temp/addBook.html", {'alert':alert})
    return render(request, "admin_temp/addBook.html")


@login_required(login_url='/admin_login')
def edit_book(request, book_id):
    user = User.objects.get(id=request.user.id)
    book=Book.objects.get(id=book_id)
    return render(request,"admin_temp/edit_book.html",{"user":user, 'book':book})



@login_required(login_url='/admin_login')
def edit_book_save(request):
    if request.method!="POST":
        return HttpResponse("Method Not Allowed")
    else:
        name = request.POST['name']
        author = request.POST['author']
        isbn = request.POST['isbn']
        category = request.POST['category']
        image = request.FILES['image']
        description = request.POST['description']

        try:
            books = Book.objects.create(name=name, author=author, isbn=isbn, category=category, description=description, image=image)
            books.save()
            alert = True
            messages.success(request,"Successfully Edited Book")
        except:
            messages.error(request,"Failed to Edit Book")
            return HttpResponseRedirect(reverse("view_books"))
    return render(request,"admin_temp/books.html")


def dash(request):
    user=User.objects.all().count()
    student_count=Student.objects.all().count()
    books=Book.objects.all().count()
    issuedbook=IssuedBook.objects.all().count()
    return render(request,"admin_temp/dash.html",{"user":user, 'books':books, 'issuedbook':issuedbook, "student_count":student_count})


@login_required(login_url = '/admin_login')
def view_books(request):
    books = Book.objects.all()
    return render(request, "admin_temp/books.html", {'books':books})

@login_required(login_url = '/admin_login')
def view_students(request):
    students = Student.objects.all()
    return render(request, "admin_temp/students.html", {'students':students})


def Search_student(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    students=Student.objects.filter(
        Q(phone__icontains=q)       
    
    )
    context = {'students':students }
    return render(request,"admin_temp/students.html",context)

def Search_book(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    books=Book.objects.filter(
        Q(isbn__icontains=q)       
    
    )
    context = {'books':books }
    return render(request,"admin_temp/books.html",context)


def returned(request,id):
    bstatus=IssuedBook.objects.get(id=id)
    bstatus.book_status="Returned"
    bstatus.save()
    return HttpResponseRedirect(reverse("view_issued_book"))



def not_returned(request,id):
    bstatus=IssuedBook.objects.get(id=id)
    bstatus.book_status="Active"
    bstatus.save()
    return HttpResponseRedirect(reverse("view_issued_book"))

 
@login_required(login_url = '/admin_login')
def issue_book(request):
    form = forms.IssueBookForm()
    if request.method == "POST":
        form = forms.IssueBookForm(request.POST)
        if form.is_valid():
            obj = models.IssuedBook()
            obj.student_id = request.POST['name2']
            obj.isbn = request.POST['isbn2']
            obj.save()
            alert = True
            return render(request, "admin_temp/issueBook.html", {'obj':obj, 'alert':alert})
    return render(request, "admin_temp/issueBook.html", {'form':form})



@login_required(login_url = '/admin_login')
def view_issued_book(request):
    issuedBooks = IssuedBook.objects.all()
    details = []
    for i in issuedBooks:

        books = list(models.Book.objects.filter(isbn=i.isbn))
        students = list(models.Student.objects.filter(user=i.student_id))
        bank=list(models.IssuedBook.objects.filter(id=i.id))
        DANTE=list(models.IssuedBook.objects.filter(issued_date=i.issued_date))
        DANTE2=list(models.IssuedBook.objects.filter(expiry_date=i.expiry_date))
        DANTE3=list(models.IssuedBook.objects.filter(book_status=i.book_status))
        i=0
        for l in books:
            t=(students[i].user,students[i].user_id,books[i].name, books[i].isbn, bank[i].id,
            DANTE[i].issued_date, DANTE2[i].expiry_date, DANTE3[i].book_status)
            i=i+1
            details.append(t)

    return render(request, "admin_temp/issued_books.html", {'issuedBooks':issuedBooks, 'details':details})



@login_required(login_url = '/student_login')
def student_issued_books(request):
    student = Student.objects.filter(user_id=request.user.id)
    issuedBooks = IssuedBook.objects.filter(student_id=student[0].user_id)
    li1 = []
  

    for i in issuedBooks:
        books = Book.objects.filter(isbn=i.isbn)
        DANTE=list(models.IssuedBook.objects.filter(issued_date=i.issued_date))
        DANTE2=list(models.IssuedBook.objects.filter(expiry_date=i.expiry_date))
        DANTE3=list(models.IssuedBook.objects.filter(book_status=i.book_status))
       
        for book in books:
            t=(request.user.id, request.user.get_full_name, book.name,book.author, books[0].isbn , DANTE[0].issued_date, DANTE2[0].expiry_date, DANTE3[0].book_status)
            li1.append(t)

    return render(request,'student/books.html',{'li1':li1})

@login_required(login_url = '/student_login')
def profile(request):
    return render(request, "student/studentHome.html")

@login_required(login_url = '/student_login')
def edit_profile(request):
    student = Student.objects.get(user=request.user)
    if request.method == "POST":
        email = request.POST['email']
        phone = request.POST['phone']
        branch = request.POST['branch']
        classroom = request.POST['classroom']
        adm_no = request.POST['roll_no']
        image = request.FILES['image']

        student.user.email = email
        student.image = image
        student.phone = phone
        student.branch = branch
        student.classroom = classroom
        student.adm_no  = adm_no 
        student.user.save()
        student.save()
        alert = True
        return render(request, "student/edit.html", {'alert':alert})
    return render(request, "student/edit.html")

def delete_book(request, myid):
    books = Book.objects.get(id=myid)
    books.delete()
    return redirect("/view_books")

def delete_student(request, myid):
    students = Student.objects.get(id=myid)
    students.delete()
    return redirect("/view_students")

def delete_issued(request, id):
    issuedbook = IssuedBook.objects.get(id=id)
    issuedbook.delete()
    return redirect("/view_books")

def change_password(request):
    if request.method == "POST":
        current_password = request.POST['current_password']
        new_password = request.POST['new_password']
        try:
            u = User.objects.get(id=request.user.id)
            if u.check_password(current_password):
                u.set_password(new_password)
                u.save()
                alert = True
                return render(request, "student/changepsw.html", {'alert':alert})
            else:
                currpasswrong = True
                return render(request, "student/changepsw.html", {'currpasswrong':currpasswrong})
        except:
            pass
    return render(request, "student/changepsw.html")

def student_registration(request):
    if request.method == "POST":
        username = request.POST['username']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']
        phone = request.POST['phone']
        branch = request.POST['branch']

        classroom = request.POST['classroom']
        image = request.FILES['image']
    
                   
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password != confirm_password:
            passnotmatch = True
            return render(request, "student/register.html", {'passnotmatch':passnotmatch})

        user = User.objects.create_user(username=username, email=email, password=password,first_name=first_name, last_name=last_name)
        student = Student.objects.create(user=user, phone=phone, branch=branch, classroom=classroom, image=image)
   
        user.save()
        student.save()
        alert = True
        return render(request, "new_student_regform.html", {'alert':alert})
    return render(request, "new_student_regform.html")

@csrf_exempt
def check_email_exist(request):
    email=request.POST.get("email")
    user_obj=User.objects.filter(email=email).exists()
    if user_obj:
        return HttpResponse(True)
    else:
        return HttpResponse(False)

@csrf_exempt
def check_username_exist(request):
    username=request.POST.get("username")
    user_obj=User.objects.filter(username=username).exists()
    if user_obj:
        return HttpResponse(True)
    else:
        return HttpResponse(False)


def student_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)

        if user is not None:
            login(request, user)
            if request.user.is_superuser:
                return HttpResponse("You are not a student!!")
            else:
                return redirect("/profile")
        else:
            alert = True
            return render(request, "student/login.html", {'alert':alert})
    return render(request, "student/login.html")

def admin_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)

        if user is not None:
            login(request, user)
            if request.user.is_superuser:
                return redirect("/add_book")
            else:
                return HttpResponse("You are not an admin.")
        else:
            alert = True
            return render(request, "admin_temp/login.html", {'alert':alert})
    return render(request, "admin_temp/login.html")

def Logout(request):
    logout(request)
    return redirect ("/")
