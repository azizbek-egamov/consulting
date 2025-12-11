from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from functools import wraps
from django.db.models import Count, Sum, Q
from main.models import ConsultingContract


# Custom decorator for ceoadmin only
def ceoadmin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if request.user.username != "ceoadmin":
            messages.warning(request, "Sizda bu bo'limga kirish huquqi yo'q.")
            return redirect("home")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@login_required(login_url='login')
@ceoadmin_required
def UserManagementPage(request):
    """Foydalanuvchilar ro'yxati"""
    users = User.objects.all().order_by('-date_joined')
    
    # Har bir foydalanuvchi uchun shartnomalar sonini hisoblash
    users_with_stats = []
    for user in users:
        contracts_count = ConsultingContract.objects.filter(created_by=user).count()
        users_with_stats.append({
            'user': user,
            'contracts_count': contracts_count
        })
    
    context = {
        'users_with_stats': users_with_stats,
        'total_users': users.count()
    }
    return render(request, 'users/list.html', context)


@login_required(login_url='login')
@ceoadmin_required
def UserCreate(request):
    """Yangi foydalanuvchi yaratish"""
    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        
        # Validatsiya
        if not first_name or not last_name or not username or not password:
            messages.warning(request, "Barcha maydonlar to'ldirilishi shart.")
            return render(request, 'users/create.html')
        
        if User.objects.filter(username=username).exists():
            messages.warning(request, f"'{username}' username allaqachon mavjud.")
            return render(request, 'users/create.html', {
                'first_name': first_name,
                'last_name': last_name,
                'username': username
            })
        
        if len(password) < 6:
            messages.warning(request, "Parol kamida 6 ta belgidan iborat bo'lishi kerak.")
            return render(request, 'users/create.html', {
                'first_name': first_name,
                'last_name': last_name,
                'username': username
            })
        
        try:
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            messages.success(request, f"Foydalanuvchi '{username}' muvaffaqiyatli yaratildi.")
            return redirect("user-management")
        except Exception as e:
            messages.warning(request, f"Foydalanuvchi yaratishda xatolik: {str(e)}")
            return render(request, 'users/create.html', {
                'first_name': first_name,
                'last_name': last_name,
                'username': username
            })
    
    return render(request, 'users/create.html')


@login_required(login_url='login')
@ceoadmin_required
def UserEdit(request, id):
    """Foydalanuvchi ma'lumotlarini tahrirlash"""
    user = get_object_or_404(User, pk=id)
    is_ceo_admin = user.username == "ceoadmin"
    
    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        username = request.POST.get("username", "").strip() if not is_ceo_admin else user.username
        
        # Validatsiya
        if not first_name or not last_name or (not is_ceo_admin and not username):
            messages.warning(request, "Barcha maydonlar to'ldirilishi shart.")
            return render(request, 'users/edit.html', {'user_obj': user, 'is_ceo_admin': is_ceo_admin})
        
        # Username o'zgargan bo'lsa, tekshirish
        if not is_ceo_admin and username != user.username:
            if User.objects.filter(username=username).exists():
                messages.warning(request, f"'{username}' username allaqachon mavjud.")
                return render(request, 'users/edit.html', {'user_obj': user, 'is_ceo_admin': is_ceo_admin})
        
        try:
            user.first_name = first_name
            user.last_name = last_name
            if not is_ceo_admin:
                user.username = username
            user.save()
            messages.success(request, f"Foydalanuvchi ma'lumotlari muvaffaqiyatli yangilandi.")
            return redirect("user-management")
        except Exception as e:
            messages.warning(request, f"Ma'lumotlarni yangilashda xatolik: {str(e)}")
            return render(request, 'users/edit.html', {'user_obj': user, 'is_ceo_admin': is_ceo_admin})
    
    return render(request, 'users/edit.html', {'user_obj': user, 'is_ceo_admin': is_ceo_admin})


@login_required(login_url='login')
@ceoadmin_required
def UserChangePassword(request, id):
    """Foydalanuvchi parolini o'zgartirish"""
    user = get_object_or_404(User, pk=id)
    
    # ceoadmin o'z parolini bu bo'limda o'zgartira olmaydi
    if user.username == "ceoadmin":
        messages.warning(request, "Siz o'z parolingizni bu bo'limda o'zgartira olmaysiz.")
        return redirect("user-management")
    
    if request.method == "POST":
        password = request.POST.get("password", "").strip()
        password_confirm = request.POST.get("password_confirm", "").strip()
        
        if not password or not password_confirm:
            messages.warning(request, "Parol maydonlari to'ldirilishi shart.")
            return render(request, 'users/change_password.html', {'user_obj': user})
        
        if password != password_confirm:
            messages.warning(request, "Parollar mos kelmaydi.")
            return render(request, 'users/change_password.html', {'user_obj': user})
        
        if len(password) < 6:
            messages.warning(request, "Parol kamida 6 ta belgidan iborat bo'lishi kerak.")
            return render(request, 'users/change_password.html', {'user_obj': user})
        
        try:
            user.set_password(password)
            user.save()
            messages.success(request, f"Foydalanuvchi paroli muvaffaqiyatli o'zgartirildi.")
            return redirect("user-management")
        except Exception as e:
            messages.warning(request, f"Parolni o'zgartirishda xatolik: {str(e)}")
            return render(request, 'users/change_password.html', {'user_obj': user})
    
    return render(request, 'users/change_password.html', {'user_obj': user})


@login_required(login_url='login')
@ceoadmin_required
def UserDelete(request, id):
    """Foydalanuvchini o'chirish"""
    user = get_object_or_404(User, pk=id)
    
    # ceoadmin o'zini o'chira olmaydi
    if user.username == "ceoadmin":
        messages.warning(request, "Siz o'zingizni o'chira olmaysiz.")
        return redirect("user-management")
    
    if request.method == "POST":
        username = user.username
        try:
            user.delete()
            messages.success(request, f"Foydalanuvchi '{username}' muvaffaqiyatli o'chirildi.")
        except Exception as e:
            messages.warning(request, f"Foydalanuvchini o'chirishda xatolik: {str(e)}")
    
    return redirect("user-management")

