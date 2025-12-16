from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Avg
from django.db.models.functions import TruncDate, TruncMonth
from datetime import datetime, timedelta, date
from main.models import Lead, ClientInformation, CallOperator, LeadStage
import logging
import json

# Logger sozlamalari
logger = logging.getLogger(__name__)


# Admin tekshiruvi
def is_admin(user):
    return user.is_staff or user.is_superuser


# Dastlabki LeadStage obyektlarini yaratish
def create_default_lead_stages():
    stages_data = [
        {
            "key": "answered",
            "name": "JAVOB BERILDI",
            "color": "#55db34",
            "description": "Mijozni qo'ngirog'iga javob berilgan",
            "order": 1,
            "is_system_stage": True,
        },
        {
            "key": "not_answered",
            "name": "JAVOB BERILMADI",
            "color": "#f39c12",
            "description": "Mijozni qo'ngirog'iga javob berilmadi",
            "order": 2,
            "is_system_stage": True,
        },
        {
            "key": "client_answered",
            "name": "MIJOZ JAVOB BERDI",
            "color": "#3c8ce7",
            "description": "Mijozga qayta qo'ng'iroq qilindi",
            "order": 3,
            "is_system_stage": True,
        },
        {
            "key": "client_not_answered",
            "name": "MIJOZ JAVOB BERMADI",
            "color": "#e74c3c",
            "description": "Mijozga qayta qo'ng'iroq qilindi, lekin mijoz javob bermadi",
            "order": 4,
            "is_system_stage": True,
        },
        {
            "key": "follow_up",
            "name": "KEYINGI ALOQA",
            "color": "#9b59b6",
            "description": "Yaqinda aloqa o'rnatish rejalashtirilgan",
            "order": 5,
            "is_system_stage": True,
        },
        {
            "key": "converted",
            "name": "MIJOZGA AYLANGAN",
            "color": "#27ae60",
            "description": "Muvaffaqiyatli mijozga aylantirilgan",
            "order": 6,
            "is_system_stage": True,
        },
    ]

    for data in stages_data:
        LeadStage.objects.get_or_create(key=data["key"], defaults=data)

    # Mavjud leadlarning stage maydonini to'g'rilash
    for lead in Lead.objects.filter(stage__isnull=True):
        # stage maydoni endi save() metodida avtomatik belgilanadi, shuning uchun shunchaki save() chaqirish yetarli
        lead.save()


@login_required
def leads_kanban(request):
    """AmoCRM ko'rinishidagi kanban board - dinamik bosqichlar bilan"""
    if request.method == "POST":
        return lead_edit(request, request.POST['lead_pk'])
    
    create_default_lead_stages()
    stages = LeadStage.objects.all().order_by("order")

    # Filter parametrlari
    today = timezone.now().date()
    # Default qiymatni 'all' ga o'zgartirdik
    date_filter_param = request.GET.get('date', 'today') 
    status_filter_param = request.GET.get('status', 'all')

    # Barcha leadlar uchun asosiy queryset
    base_leads_queryset = Lead.objects.select_related("operator", "stage").all()

    # Sana bo'yicha filtrlash
    if date_filter_param == 'today':
        base_leads_queryset = base_leads_queryset.filter(created_at__date=today)
    elif date_filter_param == 'yesterday':
        yesterday = today - timedelta(days=1)
        base_leads_queryset = base_leads_queryset.filter(created_at__date=yesterday)
    elif date_filter_param == 'week':
        week_ago = today - timedelta(days=7)
        base_leads_queryset = base_leads_queryset.filter(created_at__date__gte=week_ago)
    elif date_filter_param == 'month':
        month_ago = today - timedelta(days=30)
        base_leads_queryset = base_leads_queryset.filter(created_at__date__gte=month_ago)
    # Agar date_filter_param 'all' bo'lsa, hech qanday sana filtri qo'llanilmaydi, bu to'g'ri xatti-harakat.

    # leads_by_stage lug'atini barcha bosqich kalitlari bilan bo'sh ro'yxatlar bilan boshlash
    leads_by_stage = {stage.key: [] for stage in stages}
    leads_by_stage["follow_up_today"] = []
    leads_by_stage["follow_up_upcoming"] = []

    # Leadlarni tegishli bosqichlarga ajratish (status filtri shu yerda qo'llaniladi)
    for lead in base_leads_queryset:
        determined_stage_key = lead.stage.key if lead.stage else lead.get_current_stage_key()

        # Agar status filtri mavjud bo'lsa va lead unga mos kelmasa, o'tkazib yuborish
        if status_filter_param != 'all' and determined_stage_key != status_filter_param:
            continue

        if determined_stage_key == "follow_up":
            if lead.follow_up_date and lead.follow_up_date.date() == today:
                leads_by_stage["follow_up_today"].append(lead)
            elif lead.follow_up_date and lead.follow_up_date.date() > today:
                leads_by_stage["follow_up_upcoming"].append(lead)
        else:
            if determined_stage_key in leads_by_stage:
                leads_by_stage[determined_stage_key].append(lead)
            else:
                logger.critical(
                    f"Lead {lead.id} assigned to an unknown stage key: {determined_stage_key}. Please check Lead.get_current_stage_key() logic and default stages."
                )
                leads_by_stage["not_answered"].append(lead) # Fallback

    # Follow-up leadlarni sanash va tartiblash
    leads_by_stage["follow_up_today"].sort(
        key=lambda x: x.follow_up_date or timezone.now()
    )
    leads_by_stage["follow_up_upcoming"].sort(
        key=lambda x: x.follow_up_date or timezone.now()
    )

    # Display stages: If a specific status is filtered, only show that stage.
    # Otherwise, show all stages.
    display_stages = []
    if status_filter_param != 'all':
        for stage in stages:
            if stage.key == status_filter_param:
                display_stages.append(stage)
                break
    else:
        display_stages = stages

    # Statistikalar (faqat ko'rsatilayotgan leadlar bo'yicha)
    all_displayed_leads = []
    for stage_key, leads_list in leads_by_stage.items():
        all_displayed_leads.extend(leads_list)

    total_leads_displayed = len(all_displayed_leads)
    
    today_leads_stat = sum(1 for lead in all_displayed_leads if lead.created_at.date() == today)
    converted_today_stat = sum(1 for lead in all_displayed_leads if lead.is_converted and lead.updated_at.date() == today)
    answered_calls_stat = sum(1 for lead in all_displayed_leads if lead.call_status in ["answered", "client_answered"])
    total_calls_stat = sum(1 for lead in all_displayed_leads if lead.call_status is not None)

    operators = CallOperator.objects.all()
    is_admin_user = is_admin(request.user)
    all_stages_for_filter = LeadStage.objects.all().order_by("order") # Get all stages for filter dropdown

    context = {
        "stages": display_stages, # Only display filtered stages in the kanban board itself
        "stages_all": all_stages_for_filter, # All stages for the filter dropdown
        "leads_by_stage": leads_by_stage, # This contains leads filtered by date and status
        "total_leads": total_leads_displayed, # Total leads currently displayed in the kanban
        "today_leads": today_leads_stat, # Stats based on displayed leads
        "converted_today": converted_today_stat,
        "answered_calls": answered_calls_stat,
        "total_calls": total_calls_stat,
        "operators": operators,
        "is_admin": is_admin_user,
        "current_date_filter": date_filter_param, # Pass current filter to template
        "current_status_filter": status_filter_param, # Pass current filter to template
    }
    return render(request, "leads/kanban_board.html", context)


@login_required
@user_passes_test(is_admin)
def create_lead_stage(request):
    if request.method == "POST":
        name = request.POST.get("name")
        key = request.POST.get("key")
        color = request.POST.get("color")
        description = request.POST.get("description")
        order = request.POST.get("order", 0)

        if not name or not key or not color:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Barcha majburiy maydonlar to'ldirilishi shart.",
                },
                status=400,
            )

        if LeadStage.objects.filter(key=key).exists():
            return JsonResponse(
                {
                    "success": False,
                    "message": f'"{key}" kalitiga ega bosqich allaqachon mavjud.',
                },
                status=400,
            )

        try:
            LeadStage.objects.create(
                name=name,
                key=key,
                color=color,
                description=description,
                order=int(order),
            )
            messages.success(request, "Yangi bosqich muvaffaqiyatli yaratildi!")
            return JsonResponse({"success": True, "message": "Bosqich yaratildi"})
        except Exception as e:
            logger.error(f"Error creating lead stage: {e}", exc_info=True)
            return JsonResponse({"success": False, "message": str(e)}, status=500)

    # GET request for modal content
    return render(
        request, "leads/stage_form.html", {"form_title": "Yangi bosqich yaratish"}
    )


@login_required
@user_passes_test(is_admin)
def edit_lead_stage(request, stage_id):
    stage = get_object_or_404(LeadStage, id=stage_id)

    if request.method == "POST":
        name = request.POST.get("name")
        key = request.POST.get("key")
        color = request.POST.get("color")
        description = request.POST.get("description")
        order = request.POST.get("order", 0)

        if not name or not key or not color:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Barcha majburiy maydonlar to'ldirilishi shart.",
                },
                status=400,
            )

        if LeadStage.objects.filter(key=key).exclude(id=stage_id).exists():
            return JsonResponse(
                {
                    "success": False,
                    "message": f'"{key}" kalitiga ega bosqich allaqachon mavjud.',
                },
                status=400,
            )

        try:
            stage.name = name
            # Tizim bosqichining kalitini o'zgartirishga ruxsat bermaslik
            if not stage.is_system_stage:
                stage.key = key
            stage.color = color
            stage.description = description
            stage.order = int(order)
            stage.save()
            messages.success(request, "Bosqich muvaffaqiyatli tahrirlandi!")
            return JsonResponse({"success": True, "message": "Bosqich tahrirlandi"})
        except Exception as e:
            logger.error(f"Error editing lead stage {stage_id}: {e}", exc_info=True)
            return JsonResponse({"success": False, "message": str(e)}, status=500)

    return render(
        request,
        "leads/stage_form.html",
        {"form_title": "Bosqichni tahrirlash", "stage": stage},
    )


@login_required
@user_passes_test(is_admin)
def delete_lead_stage(request, stage_id):
    stage = get_object_or_404(LeadStage, id=stage_id)

    if stage.is_system_stage:
        return JsonResponse(
            {"success": False, "message": "Tizim bosqichlarini o'chirish mumkin emas."},
            status=403,
        )

    if request.method == "POST":
        try:
            # Bosqichni o'chirishdan oldin, unga bog'langan leadlarni 'not_answered' bosqichiga o'tkazamiz
            not_answered_stage = LeadStage.objects.get(key="not_answered")
            Lead.objects.filter(stage=stage).update(stage=not_answered_stage)

            stage.delete()
            messages.success(request, "Bosqich muvaffaqiyatli o'chirildi!")
            return JsonResponse({"success": True, "message": "Bosqich o'chirildi"})
        except LeadStage.DoesNotExist:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Zaxira bosqich topilmadi. Iltimos, tizimni qayta sozlang.",
                },
                status=500,
            )
        except Exception as e:
            logger.error(f"Error deleting lead stage {stage_id}: {e}", exc_info=True)
            return JsonResponse({"success": False, "message": str(e)}, status=500)

    return JsonResponse({"success": False, "message": "Noto'g'ri so'rov"}, status=400)


@login_required
def update_lead_stage(request):
    """Lead bosqichini yangilash (dinamik bosqichlar orqali)"""
    if request.method == "POST":
        # Faqat adminlar bosqichni o'zgartira olsin
        if not is_admin(request.user):
            return JsonResponse(
                {
                    "success": False,
                    "message": "Sizda lead bosqichini o'zgartirish huquqi yo'q.",
                },
                status=403,
            )  # Forbidden

        try:
            lead_id = request.POST.get("lead_id")
            new_stage_key = request.POST.get("new_stage")
            follow_up_date_str = request.POST.get("follow_up_date")
            follow_up_time_str = request.POST.get("follow_up_time")
            notes = request.POST.get("notes", "")

            lead = get_object_or_404(Lead, id=lead_id)
            new_stage_obj = get_object_or_404(LeadStage, key=new_stage_key)

            # Eski bosqichni aniqlash
            current_stage_key = (
                lead.stage.key if lead.stage else lead.get_current_stage_key()
            )
            stage_changed = new_stage_key != current_stage_key

            # Leadning asosiy holat maydonlarini yangi bosqichga moslashtirish
            # Avvalgi holatlarni tozalash
            lead.call_status = None
            lead.is_converted = False
            lead.follow_up_date = None

            if new_stage_key == "answered":
                lead.call_status = "answered"
            elif new_stage_key == "not_answered":
                lead.call_status = "not_answered"
            elif new_stage_key == "client_answered":
                lead.call_status = "client_answered"
            elif new_stage_key == "client_not_answered":
                lead.call_status = "client_not_answered"
            elif new_stage_key == "follow_up":
                # Agar sana va vaqt berilgan bo'lsa, ularni ishlatish
                if follow_up_date_str and follow_up_time_str:
                    try:
                        follow_up_datetime = datetime.strptime(
                            f"{follow_up_date_str} {follow_up_time_str}",
                            "%Y-%m-%d %H:%M",
                        )
                        lead.follow_up_date = timezone.make_aware(follow_up_datetime)
                    except ValueError:
                        lead.follow_up_date = timezone.now() + timedelta(
                            days=3
                        )  # Fallback
                else:
                    lead.follow_up_date = timezone.now() + timedelta(days=3)  # Default

                if notes:
                    if lead.notes:
                        lead.notes += f"\n\nKeyingi aloqa: {notes}"
                    else:
                        lead.notes = f"Keyingi aloqa: {notes}"
            elif new_stage_key == "converted":
                if not lead.is_converted:  # Faqat bir marta mijozga aylantirish
                    client_name = lead.client_name or f"Lead #{lead.id}"
                    client = ClientInformation.objects.create(
                        full_name=client_name,
                        phone=lead.phone_number,
                        heard="Lead orqali",
                    )
                    lead.converted_client = client  # Bog'lash
                lead.is_converted = True

            # Leadning stage maydonini yangilash
            lead.stage = new_stage_obj
            lead.updated_at = timezone.now()
            lead.save()  # Bu yerda stage maydoni allaqachon belgilangan bo'ladi

            return JsonResponse(
                {
                    "success": True,
                    "message": "Lead bosqichi yangilandi",
                    "reload_page": stage_changed,  # Agar bosqich o'zgargan bo'lsa, sahifani yangilash
                    "client_name": lead.client_name,
                    "lead_id": lead.id,
                    "new_call_status": lead.call_status,
                    "new_follow_up_date": (
                        lead.follow_up_date.strftime("%Y-%m-%d %H:%M")
                        if lead.follow_up_date
                        else None
                    ),
                    "new_notes": lead.notes,
                    "new_phone_number": lead.phone_number,
                    "new_operator_name": lead.operator.full_name,
                    "new_created_at": lead.created_at.strftime("%d.%m %H:%M"),
                    "new_duration_display": (
                        lead.get_duration_display() if lead.call_duration else "-"
                    ),
                    "audio_recording_url": (
                        lead.audio_recording.url if lead.audio_recording else None
                    ),
                    "new_stage_key": new_stage_key,  # Yangi bosqich kaliti
                }
            )

        except Exception as e:
            logger.error(f"Error updating lead stage: {e}", exc_info=True)
            return JsonResponse({"success": False, "message": str(e)}, status=500)

    return JsonResponse({"success": False, "message": "Noto'g'ri so'rov"}, status=400)


@login_required
@user_passes_test(is_admin)
def update_stage_order(request):
    """LeadStage bosqichlarining tartibini yangilash"""
    # Bu funksiya endi ishlatilmaydi, chunki bosqichlarni sudrab o'tkazish funksiyasi olib tashlandi.
    return JsonResponse(
        {
            "success": False,
            "message": "Bosqich tartibini yangilash funksiyasi o'chirilgan.",
        },
        status=400,
    )


@login_required
def leads_list(request):
    """Leadlar ro'yxati (eski ko'rinish)"""
    leads = Lead.objects.all()

    # Filterlar
    search = request.GET.get("search", "")
    status = request.GET.get("status", "")
    date_filter = request.GET.get("date", "")
    converted = request.GET.get("converted", "")
    operator_id = request.GET.get("operator", "")

    if search:
        leads = leads.filter(
            Q(phone_number__icontains=search)
            | Q(client_name__icontains=search)
            | Q(notes__icontains=search)
        )

    if status:
        leads = leads.filter(call_status=status)

    if operator_id:
        leads = leads.filter(operator_id=operator_id)

    if date_filter:
        today = timezone.now().date()
        if date_filter == "today":
            leads = leads.filter(created_at__date=today)
        elif date_filter == "yesterday":
            yesterday = today - timedelta(days=1)
            leads = leads.filter(created_at__date=yesterday)
        elif date_filter == "week":
            week_ago = today - timedelta(days=7)
            leads = leads.filter(created_at__date__gte=week_ago)
        elif date_filter == "month":
            month_ago = today - timedelta(days=30)
            leads = leads.filter(created_at__date__gte=month_ago)

    if converted == "converted":
        leads = leads.filter(is_converted=True)
    elif converted == "not_converted":
        leads = leads.filter(is_converted=False)

    # Statistikalar
    total_leads = Lead.objects.count()
    today_leads = Lead.objects.filter(created_at__date=timezone.now().date()).count()
    answered_leads = Lead.objects.filter(
        Q(call_status="answered") | Q(call_status="client_answered")
    ).count()
    converted_leads = Lead.objects.filter(is_converted=True).count()
    not_answered = Lead.objects.filter(
        Q(call_status="not_answered") | Q(call_status="client_not_answered")
    ).count()

    # Operatorlar
    operators = CallOperator.objects.all()

    context = {
        "leads": leads,
        "total_leads": total_leads,
        "today_leads": today_leads,
        "answered_leads": answered_leads,
        "converted_leads": converted_leads,
        "not_answered": not_answered,
        "status_choices": Lead.CALL_STATUS_CHOICES,
        "operators": operators,
        "current_filters": {
            "search": search,
            "status": status,
            "date": date_filter,
            "converted": converted,
            "operator": operator_id,
        },
    }

    return render(request, "leads/leads_list.html", context)


@login_required
def lead_create(request):
    """Yangi lead yaratish"""
    if request.method == "POST":
        try:
            phone_number = request.POST.get("phone_number")
            client_name = request.POST.get("client_name", "")
            operator_id = request.POST.get("operator")
            call_status = request.POST.get("call_status")
            notes = request.POST.get("notes", "")

            # Davomiylikni olish
            duration_input = request.POST.get("duration_input", "")
            call_duration = None

            if duration_input:
                try:
                    # HH:MM:SS formatini parse qilish
                    if ":" in duration_input:
                        parts = duration_input.split(":")
                        if len(parts) == 3:
                            hours = int(parts[0])
                            minutes = int(parts[1])
                            seconds = int(parts[2])
                            call_duration = timedelta(
                                hours=hours, minutes=minutes, seconds=seconds
                            )
                        elif len(parts) == 2:
                            minutes = int(parts[0])
                            seconds = int(parts[1])
                            call_duration = timedelta(minutes=minutes, seconds=seconds)
                    else:
                        # Faqat soniyalar
                        total_seconds = int(duration_input)
                        call_duration = timedelta(seconds=total_seconds)
                except ValueError:
                    pass

            # Keyingi qo'ng'iroq sanasi
            follow_up_date = request.POST.get("follow_up_date")
            follow_up_time = request.POST.get("follow_up_time")
            follow_up_datetime = None

            if follow_up_date and follow_up_time:
                follow_up_datetime = datetime.strptime(
                    f"{follow_up_date} {follow_up_time}", "%Y-%m-%d %H:%M"
                )
                follow_up_datetime = timezone.make_aware(follow_up_datetime)

            # Operator
            operator = get_object_or_404(CallOperator, id=operator_id)

            # Lead yaratishdan oldin stage ni aniqlash
            temp_lead = Lead(
                phone_number=phone_number,
                client_name=client_name,
                operator=operator,
                call_status=call_status if call_status else None,
                call_duration=call_duration,
                notes=notes,
                follow_up_date=follow_up_datetime,
            )
            initial_stage_key = temp_lead.get_current_stage_key()
            initial_stage_obj = get_object_or_404(LeadStage, key=initial_stage_key)

            lead = Lead.objects.create(
                phone_number=phone_number,
                client_name=client_name,
                operator=operator,
                call_status=call_status if call_status else None,
                call_duration=call_duration,
                notes=notes,
                follow_up_date=follow_up_datetime,
                stage=initial_stage_obj,  # Stage maydonini aniq belgilash
            )

            # Audio fayl yuklash
            if "audio_recording" in request.FILES:
                lead.audio_recording = request.FILES["audio_recording"]
                lead.save()

            messages.success(request, "Lead muvaffaqiyatli yaratildi!")

            # Agar kanban board dan kelgan bo'lsa, u yerga qaytarish
            if request.POST.get("from_kanban"):
                return redirect("leads_kanban")
            else:
                return redirect("leads_list")

        except Exception as e:
            logger.error(f"Error creating lead: {e}", exc_info=True)
            messages.warning(request, f"Xatolik: {str(e)}")

    # Operatorlar ro'yxati
    operators = CallOperator.objects.all()

    context = {
        "status_choices": Lead.CALL_STATUS_CHOICES,
        "operators": operators,
        "from_kanban": request.GET.get("from_kanban", False),
    }
    return render(request, "leads/lead_create.html", context)


@login_required
def lead_edit(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if request.method == "POST":
        try:
            phone_number = request.POST.get("phone_number", "").strip()
            client_name = request.POST.get("client_name", "").strip()
            call_status = request.POST.get("call_status", "").strip()
            notes = request.POST.get("notes", "").strip()

            if not phone_number:
                if is_ajax:
                    return JsonResponse({"success": False, "message": "Telefon raqami kiritilishi shart"}, status=400)
                messages.warning(request, "Telefon raqami kiritilishi shart")
                return redirect("leads_kanban")

            temp_lead_call_status = call_status if call_status else None

            follow_up_date_str = request.POST.get("follow_up_date", "").strip()
            follow_up_time_str = request.POST.get("follow_up_time", "").strip()
            temp_follow_up_datetime = None
            if follow_up_date_str and follow_up_time_str:
                try:
                    temp_follow_up_datetime = datetime.strptime(
                        f"{follow_up_date_str} {follow_up_time_str}", "%Y-%m-%d %H:%M"
                    )
                    temp_follow_up_datetime = timezone.make_aware(temp_follow_up_datetime)
                except ValueError:
                    pass

            lead.phone_number = phone_number
            lead.client_name = client_name or None
            lead.call_status = temp_lead_call_status
            lead.notes = notes or None
            lead.follow_up_date = temp_follow_up_datetime

            if not lead.call_duration:
                duration_input = request.POST.get("duration_input", "").strip()
                if duration_input:
                    try:
                        if ":" in duration_input:
                            parts = duration_input.split(":")
                            if len(parts) == 3:
                                hours, minutes, seconds = map(int, parts)
                                lead.call_duration = timedelta(hours=hours, minutes=minutes, seconds=seconds)
                            elif len(parts) == 2:
                                minutes, seconds = map(int, parts)
                                lead.call_duration = timedelta(minutes=minutes, seconds=seconds)
                        else:
                            lead.call_duration = timedelta(seconds=int(duration_input))
                    except (ValueError, TypeError):
                        pass

            if "audio_recording" in request.FILES and request.FILES["audio_recording"]:
                lead.audio_recording = request.FILES["audio_recording"]

            lead.updated_at = timezone.now()

            old_stage_key = lead.stage.key if lead.stage else lead.get_current_stage_key()
            determined_stage_key = lead.get_current_stage_key()
            lead.stage = get_object_or_404(LeadStage, key=determined_stage_key)

            lead.save()

            new_stage_key = lead.stage.key if lead.stage else lead.get_current_stage_key()
            stage_changed = new_stage_key != old_stage_key

            if is_ajax:
                return JsonResponse({
                    "success": True,
                    "message": "Lead muvaffaqiyatli yangilandi",
                    "reload_page": stage_changed,
                    "client_name": lead.client_name,
                    "lead_id": lead.id,
                    "new_call_status": lead.call_status,
                    "new_follow_up_date": lead.follow_up_date.strftime("%Y-%m-%d %H:%M") if lead.follow_up_date else None,
                    "new_notes": lead.notes,
                    "new_phone_number": lead.phone_number,
                    "new_operator_name": lead.operator.full_name,
                    "new_created_at": lead.created_at.strftime("%d.%m %H:%M"),
                    "new_duration_display": lead.get_duration_display() if lead.call_duration else "-",
                    "audio_recording_url": lead.audio_recording.url if lead.audio_recording else None,
                    "new_stage_key": new_stage_key,
                })
            else:
                messages.success(request, "Lead muvaffaqiyatli yangilandi")
                return redirect("leads_kanban")

        except Exception as e:
            logger.error(f"Lead edit error for lead {lead_id}: {str(e)}", exc_info=True)
            if is_ajax:
                return JsonResponse({"success": False, "message": str(e)}, status=500)
            messages.warning(request, f"Xatolik: {str(e)}")
            return redirect("leads_kanban")

    # GET so‘rov uchun forma rendering
    total_seconds = int(lead.call_duration.total_seconds()) if lead.call_duration else 0
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    operators = CallOperator.objects.all()
    context = {
        "lead": lead,
        "status_choices": Lead.CALL_STATUS_CHOICES,
        "operators": operators,
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds,
        "from_kanban": request.GET.get("from_kanban", False),
    }
    return render(request, "leads/lead_edit.html", context)



@login_required
def lead_detail(request, lead_id):
    """Lead tafsilotlari"""
    lead = get_object_or_404(Lead, id=lead_id)

    context = {"lead": lead, "from_kanban": request.GET.get("from_kanban", False)}
    return render(request, "leads/lead_detail.html", context)


@login_required
@user_passes_test(is_admin)
def lead_delete(request, lead_id):
    """Lead o'chirish"""
    try:
        lead = get_object_or_404(Lead, id=lead_id)
        lead.delete()
        return JsonResponse({"success": True, "message": "Lead o'chirildi"})
    except Exception as e:
        logger.error(f"Error deleting lead {lead_id}: {e}", exc_info=True)
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
def lead_convert_to_client(request, lead_id):
    """Lead ni mijozga aylantirish"""
    lead = get_object_or_404(Lead, id=lead_id)

    if request.method == "POST":
        try:
            # Yangi mijoz yaratish
            client = ClientInformation.objects.create(
                full_name=request.POST.get("full_name", lead.client_name or ""),
                phone=lead.phone_number,
                heard="Lead orqali",
            )

            # Lead ni yangilash
            lead.is_converted = True
            lead.updated_at = timezone.now()
            # Stage ni 'converted' ga o'tkazish
            converted_stage = LeadStage.objects.get(key="converted")
            lead.stage = converted_stage
            lead.save()

            messages.success(
                request, f"Lead muvaffaqiyatli mijozga aylantirildi: {client.full_name}"
            )

            # Agar kanban board dan kelgan bo'lsa, u yerga qaytarish
            if request.POST.get("from_kanban"):
                return redirect("leads_kanban")
            else:
                return redirect("leads_list")

        except Exception as e:
            logger.error(
                f"Error converting lead {lead_id} to client: {e}", exc_info=True
            )
            messages.warning(request, f"Xatolik: {str(e)}")

    context = {"lead": lead, "from_kanban": request.GET.get("from_kanban", False)}
    return render(request, "leads/lead_convert.html", context)


@login_required
def leads_dashboard(request):
    """Leadlar dashboard"""
    # Statistikalar
    total_leads = Lead.objects.count()
    today_leads = Lead.objects.filter(created_at__date=timezone.now().date()).count()
    answered_leads = Lead.objects.filter(
        Q(call_status="answered") | Q(call_status="client_answered")
    ).count()
    converted_leads = Lead.objects.filter(is_converted=True).count()

    # Holatlar bo'yicha statistika
    status_stats = []
    for status_code, status_name in Lead.CALL_STATUS_CHOICES:
        count = Lead.objects.filter(call_status=status_code).count()
        status_stats.append(
            {
                "name": status_name,
                "count": count,
                "percentage": round(
                    (count / total_leads * 100) if total_leads > 0 else 0, 1
                ),
            }
        )

    # Operatorlar bo'yicha statistika
    operator_stats = []
    operators = CallOperator.objects.annotate(
        lead_count=Count("lead"),
        converted_count=Count("lead", filter=Q(lead__is_converted=True)),
    )

    for operator in operators:
        conversion_rate = (
            (operator.converted_count / operator.lead_count * 100)
            if operator.lead_count > 0
            else 0
        )
        operator_stats.append(
            {
                "name": operator.full_name,
                "total_leads": operator.lead_count,
                "converted": operator.converted_count,
                "conversion_rate": round(conversion_rate, 1),
            }
        )

    # Oxirgi leadlar
    recent_leads = Lead.objects.order_by("-created_at")[:10]
    answered_calls = Lead.objects.filter(
        Q(call_status="answered") | Q(call_status="client_answered")
    ).count()
    context = {
        "total_leads": total_leads,
        "today_leads": today_leads,
        "answered_calls": answered_calls,
        "converted_leads": converted_leads,
        "status_stats": status_stats,
        "operator_stats": operator_stats,
        "recent_leads": recent_leads,
    }

    return render(request, "leads/leads_dashboard.html", context)


@login_required
def lead_quick_create(request):
    """Tez lead yaratish (kanban board uchun)"""
    if request.method == "POST":
        try:
            phone_number = request.POST.get("phone_number")
            client_name = request.POST.get("client_name", "")
            notes = request.POST.get("notes", "")
            stage_key = request.POST.get(
                "stage", "not_answered"
            )  # 'new' o'rniga 'not_answered' ga o'zgartirildi

            if not phone_number:
                return JsonResponse(
                    {"success": False, "message": "Telefon raqami kiritilishi shart"},
                    status=400,
                )

            # Birinchi operatorni olish (yoki default operator)
            operator = CallOperator.objects.first()
            if not operator:
                return JsonResponse(
                    {"success": False, "message": "Hech qanday operator topilmadi"},
                    status=500,
                )

            # Bosqichga qarab call_status va follow_up_date ni belgilash
            call_status = None
            follow_up_date = None
            is_converted = False

            if stage_key == "answered":
                call_status = "answered"
            elif stage_key == "not_answered":
                call_status = "not_answered"
            elif stage_key == "client_answered":
                call_status = "client_answered"
            elif stage_key == "client_not_answered":
                call_status = "client_not_answered"
            elif stage_key == "follow_up":
                follow_up_date = timezone.now() + timedelta(days=3)
            elif stage_key == "converted":
                is_converted = True

            # LeadStage obyektini olish
            stage_obj = get_object_or_404(LeadStage, key=stage_key)

            # Lead yaratish
            lead = Lead.objects.create(
                phone_number=phone_number,
                client_name=client_name,
                operator=operator,
                call_status=call_status,
                notes=notes,
                follow_up_date=follow_up_date,
                is_converted=is_converted,
                stage=stage_obj,  # stage maydonini to'g'ridan-to'g'ri belgilash
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": "Lead muvaffaqiyatli yaratildi!",
                    "lead_id": lead.id,
                    "client_name": lead.client_name,
                    "phone_number": lead.phone_number,
                    "call_status": lead.call_status,
                    "created_at": lead.created_at.strftime("%d.%m %H:%M"),
                    "operator_name": lead.operator.full_name,
                    "follow_up_date": (
                        lead.follow_up_date.strftime("%Y-%m-%d %H:%M")
                        if lead.follow_up_date
                        else None
                    ),
                    "notes": lead.notes,
                    "duration_display": (
                        lead.get_duration_display() if lead.call_duration else "-"
                    ),
                    "audio_recording_url": (
                        lead.audio_recording.url if lead.audio_recording else None
                    ),
                    "stage_key": lead.stage.key,  # Yangi stage_key ni qaytarish
                }
            )

        except Exception as e:
            logger.error(f"Error quick creating lead: {e}", exc_info=True)
            return JsonResponse({"success": False, "message": str(e)}, status=500)

    return JsonResponse({"success": False, "message": "Noto'g'ri so'rov"}, status=400)


@login_required
def leads_statistics_view(request):
    """Leadlar bo'yicha statistikalar sahifasi"""

    # Default sana filtrlari
    end_date_str = request.GET.get('end_date', date.today().strftime('%Y-%m-%d'))
    start_date_str = request.GET.get('start_date', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        messages.warning(request, "Noto'g'ri sana formati kiritildi.")
        start_date = (date.today() - timedelta(days=30)).date()
        end_date = date.today().date()
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

    # Barcha leadlar uchun asosiy queryset
    leads_queryset = Lead.objects.filter(created_at__date__range=(start_date, end_date))

    # Qo'shimcha filtrlarni qo'llash
    selected_operator_id = request.GET.get('operator_id', '')
    selected_stage_id = request.GET.get('stage_id', '')
    selected_call_status = request.GET.get('call_status', '')
    selected_converted_only = request.GET.get('converted_only', '')

    if selected_operator_id and selected_operator_id.isdigit():
        leads_queryset = leads_queryset.filter(operator_id=selected_operator_id)
    if selected_stage_id and selected_stage_id.isdigit():
        leads_queryset = leads_queryset.filter(stage_id=selected_stage_id)
    if selected_call_status:
        leads_queryset = leads_queryset.filter(call_status=selected_call_status)
    if selected_converted_only == 'true':
        leads_queryset = leads_queryset.filter(is_converted=True)

    # --- Grafiklar uchun ma'lumotlarni tayyorlash ---

    # 1. Kunlik qo‘shilgan Leadlar soni (Line Chart)
    daily_leads_count_data = leads_queryset.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')

    dates_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    daily_counts_map = {d['date'].strftime('%Y-%m-%d'): d['count'] for d in daily_leads_count_data}
    
    daily_leads_dates = [d.strftime('%Y-%m-%d') for d in dates_range]
    daily_leads_counts = [daily_counts_map.get(d.strftime('%Y-%m-%d'), 0) for d in dates_range]

    # 2. Operatorlar bo‘yicha Leadlar soni (Bar Chart)
    operator_leads_count_data = leads_queryset.filter(operator__isnull=False).values(
        'operator__full_name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    operator_names = [op['operator__full_name'] for op in operator_leads_count_data]
    operator_counts = [op['count'] for op in operator_leads_count_data]

    # 3. Leadlar bosqichlar bo‘yicha taqsimoti (Pie Chart)
    stage_distribution_data = leads_queryset.filter(stage__isnull=False).values(
        'stage__name'
    ).annotate(
        count=Count('id')
    )
    stage_pie_data = [{'name': d['stage__name'], 'value': d['count']} for d in stage_distribution_data]

    # 4. Qo‘ng‘iroq holati bo‘yicha Leadlar (Doughnut Chart)
    call_status_distribution_data = leads_queryset.values(
        'call_status'
    ).annotate(
        count=Count('id')
    )
    call_status_map = dict(Lead.CALL_STATUS_CHOICES)
    call_status_doughnut_data = [
        {'name': call_status_map.get(d['call_status'], d['call_status']), 'value': d['count']}
        for d in call_status_distribution_data if d['call_status']
    ]

    # 5. Leaddagi o‘rtacha qo‘ng‘iroq davomiyligi (kunlar bo‘yicha) (Line Chart)
    avg_call_duration_daily_data = leads_queryset.filter(call_duration__isnull=False).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        avg_duration=Avg('call_duration')
    ).order_by('date')

    avg_duration_map = {d['date'].strftime('%Y-%m-%d'): d['avg_duration'].total_seconds() if d['avg_duration'] else 0 for d in avg_call_duration_daily_data}
    avg_duration_dates = [d.strftime('%Y-%m-%d') for d in dates_range]
    avg_duration_values = [avg_duration_map.get(d.strftime('%Y-%m-%d'), 0) for d in dates_range]

    # 6. Har bir operator bo‘yicha qo‘ng‘iroq holati (Stacked Bar Chart)
    operator_call_status_data = leads_queryset.filter(operator__isnull=False).values(
        'operator__full_name', 'call_status'
    ).annotate(
        count=Count('id')
    ).order_by('operator__full_name', 'call_status')

    # ECharts stacked bar uchun ma'lumotlarni qayta tuzish
    operators_for_stacked = sorted(list(set([d['operator__full_name'] for d in operator_call_status_data])))
    call_statuses_for_stacked = sorted(
    [d['call_status'] for d in operator_call_status_data if d['call_status'] is not None]
)
    
    stacked_series = []
    for status_code in call_statuses_for_stacked:
        status_name = call_status_map.get(status_code, status_code)
        data_points = []
        for op_name in operators_for_stacked:
            count = next((d for d in operator_call_status_data if d['operator__full_name'] == op_name and d['call_status'] == status_code), 0)
            data_points.append(count)
        stacked_series.append({
            'name': status_name,
            'type': 'bar',
            'stack': 'total',
            'emphasis': {'focus': 'series'},
            'data': data_points
        })

    # 7. Har kunlik konversiyaga aylangan leadlar (Line Chart)
    daily_converted_leads_data = leads_queryset.filter(is_converted=True).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')

    converted_counts_map = {d['date'].strftime('%Y-%m-%d'): d['count'] for d in daily_converted_leads_data}
    daily_converted_dates = [d.strftime('%Y-%m-%d') for d in dates_range]
    daily_converted_counts = [converted_counts_map.get(d.strftime('%Y-%m-%d'), 0) for d in dates_range]

    # 8. Bosqichlar bo‘yicha yangi leadlar soni (Horizontal Bar Chart) - Chart 3 bilan bir xil ma'lumot, faqat vizualizatsiya boshqacha
    # stage_distribution_data dan foydalanamiz
    stage_horizontal_bar_names = [d['stage__name'] for d in stage_distribution_data]
    stage_horizontal_bar_counts = [d['count'] for d in stage_distribution_data]

    # 9. Follow-up date (keyingi aloqa) bo‘yicha rejalashtirilgan leadlar (Bar Chart)
    follow_up_leads_data = leads_queryset.filter(follow_up_date__isnull=False).annotate(
        date=TruncDate('follow_up_date')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    follow_up_dates_map = {d['date'].strftime('%Y-%m-%d'): d['count'] for d in follow_up_leads_data}
    follow_up_chart_dates = [d.strftime('%Y-%m-%d') for d in dates_range]
    follow_up_chart_counts = [follow_up_dates_map.get(d.strftime('%Y-%m-%d'), 0) for d in dates_range]

    # 10. Leadlar oylik tahlili (faoliyat trendi) (Multi-line Chart)
    monthly_operator_leads_data = leads_queryset.filter(operator__isnull=False).annotate(
        month=TruncMonth('created_at')
    ).values('month', 'operator__full_name').annotate(
        count=Count('id')
    ).order_by('month', 'operator__full_name')

    # Multi-line chart uchun ma'lumotlarni qayta tuzish
    all_months = sorted(list(set([d['month'].strftime('%Y-%m') for d in monthly_operator_leads_data])))
    all_operators_for_multi_line = sorted(list(set([d['operator__full_name'] for d in monthly_operator_leads_data])))

    multi_line_series = []
    for op_name in all_operators_for_multi_line:
        data_points = []
        for month_str in all_months:
            month_data = next((d for d in monthly_operator_leads_data if d['operator__full_name'] == op_name and d['month'].strftime('%Y-%m') == month_str), None)
            data_points.append(month_data['count'] if month_data else 0)
        multi_line_series.append({
            'name': op_name,
            'type': 'line',
            'smooth': True,
            'data': data_points
        })

    # Filtrlash uchun barcha operatorlar, bosqichlar va qo'ng'iroq holatlari
    all_operators = CallOperator.objects.all()
    all_stages = LeadStage.objects.all().order_by('order')
    all_call_statuses = Lead.CALL_STATUS_CHOICES

    context = {
        'start_date': start_date_str,
        'end_date': end_date_str,
        'selected_operator_id': selected_operator_id,
        'selected_stage_id': selected_stage_id,
        'selected_call_status': selected_call_status,
        'selected_converted_only': selected_converted_only,

        'daily_leads_dates': json.dumps(daily_leads_dates),
        'daily_leads_counts': json.dumps(daily_leads_counts),

        'operator_names': json.dumps(operator_names),
        'operator_counts': json.dumps(operator_counts),

        'stage_pie_data': json.dumps(stage_pie_data),

        'call_status_doughnut_data': json.dumps(call_status_doughnut_data),

        'avg_duration_dates': json.dumps(avg_duration_dates),
        'avg_duration_values': json.dumps(avg_duration_values),

        'operators_for_stacked': json.dumps(operators_for_stacked),
        'stacked_series': json.dumps(stacked_series),

        'daily_converted_dates': json.dumps(daily_converted_dates),
        'daily_converted_counts': json.dumps(daily_converted_counts),

        'stage_horizontal_bar_names': json.dumps(stage_horizontal_bar_names),
        'stage_horizontal_bar_counts': json.dumps(stage_horizontal_bar_counts),

        'follow_up_chart_dates': json.dumps(follow_up_chart_dates),
        'follow_up_chart_counts': json.dumps(follow_up_chart_counts),

        'all_months_multi_line': json.dumps(all_months),
        'multi_line_series': json.dumps(multi_line_series),

        'all_operators': all_operators,
        'all_stages': all_stages,
        'all_call_statuses': all_call_statuses,
    }
    return render(request, 'leads/leads_statistics.html', context)
