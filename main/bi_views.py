from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from main.models import Client, Rasrochka, City, Building, Expense, ExpenseType, Lead, LeadStage, Home, ConsultingContract, ConsultingContract
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncDate
from datetime import datetime, timedelta
from django.utils import timezone
import json
import logging

logger = logging.getLogger(__name__)

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

# Custom decorator for user authentication and username check
def user_passes_test(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if request.user.username == "financeadmin":
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def _get_common_filters(request):
    """Helper to parse common filter parameters."""
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    contract_status = request.GET.get('status')
    lead_stage_id = request.GET.get('lead_stage')
    expense_type_id = request.GET.get('expense_type')

    today = timezone.now().date()
    default_start_date = today - timedelta(days=90)
    default_end_date = today

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else default_start_date
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else default_end_date
    except ValueError:
        start_date = default_start_date
        end_date = default_end_date
        logger.error(f"Invalid date format provided: start_date={start_date_str}, end_date={end_date_str}. Using default dates.")

    filters = {
        'contract_filters': {},
        'payment_filters': {'pay_date__date__range': (start_date, end_date)},
        'expense_filters': {'created__date__range': (start_date, end_date)},
        'lead_filters': {'created_at__date__range': (start_date, end_date)},
        'start_date': start_date,
        'end_date': end_date,
        'selected_contract_status': contract_status or '',
        'selected_lead_stage_id': int(lead_stage_id) if lead_stage_id and str(lead_stage_id).isdigit() else '',
        'selected_expense_type_id': int(expense_type_id) if expense_type_id and str(expense_type_id).isdigit() else '',
    }

    if contract_status:
        filters['contract_filters']['status'] = contract_status
    if lead_stage_id and lead_stage_id.isdigit():
        filters['lead_filters']['stage__id'] = lead_stage_id
    if expense_type_id and expense_type_id.isdigit():
        filters['expense_filters']['expense_type__id'] = expense_type_id

    return filters

@login_required(login_url='login')
@user_passes_test
def contracts_payments_dashboard_view(request):
    """Dashboard for Contracts and Payments statistics."""
    filters = _get_common_filters(request)
    contract_filters = filters['contract_filters']
    start_date = filters['start_date']
    end_date = filters['end_date']

    # Chart 1: Daily Contract Creation - yangi ConsultingContract modelidan
    daily_contracts = ConsultingContract.objects.filter(
        created_at__date__range=(start_date, end_date),
        **contract_filters
    ).annotate(
        created_date=TruncDate('created_at')
    ).values('created_date').annotate(
        count=Count('id')
    ).order_by('created_date')
    daily_contract_dates = [d['created_date'].strftime('%Y-%m-%d') if d['created_date'] else '' for d in daily_contracts]
    daily_contract_counts = [d['count'] for d in daily_contracts]

    # Agar ma'lumot bo'sh bo'lsa, default qiymatlar
    if not daily_contract_dates:
        daily_contract_dates = []
        daily_contract_counts = []

    # Chart 2: Contracts by Status (Pie Chart) - yangi ConsultingContract modelidan
    contracts_by_status = ConsultingContract.objects.filter(**contract_filters).values('status').annotate(count=Count('id'))
    status_pie_data = []
    for d in contracts_by_status:
        if d['status']:
            status_display = dict(ConsultingContract.StatusChoices.choices).get(d['status'], d['status'])
            status_pie_data.append({'name': status_display, 'value': d['count']})

    # Chart 3: Total Revenue Over Time (Line Chart) - yangi ConsultingContract modelidan
    # To'lovlar ma'lumotlari uchun amount_paid va created_at ishlatamiz
    revenue_over_time = ConsultingContract.objects.filter(
        amount_paid__gt=0,
        created_at__date__range=(start_date, end_date)
    ).annotate(
        payment_date=TruncDate('created_at')
    ).values('payment_date').annotate(
        total_paid=Sum('amount_paid')
    ).order_by('payment_date')
    revenue_dates = [d['payment_date'].strftime('%Y-%m-%d') if d['payment_date'] else '' for d in revenue_over_time]
    revenue_amounts = [int(d['total_paid'] or 0) for d in revenue_over_time]

    # Agar ma'lumot bo'sh bo'lsa, default qiymatlar
    if not revenue_dates:
        revenue_dates = []
        revenue_amounts = []

    # Chart 6: Debt Status Distribution (Pie Chart) - yangi ConsultingContract modelidan
    consulting_contracts = ConsultingContract.objects.filter(**contract_filters)
    debtors_count = consulting_contracts.filter(amount_paid__lt=F('total_service_fee')).count()
    no_debtors_count = consulting_contracts.filter(amount_paid__gte=F('total_service_fee')).count()
    debt_pie_data = [
        {'name': 'Qarzdorlar', 'value': debtors_count},
        {'name': "To'liq to'laganlar", 'value': no_debtors_count}
    ]

    all_contract_statuses = ConsultingContract.StatusChoices.choices

    context = {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'all_contract_statuses': all_contract_statuses,
        'selected_contract_status': filters['selected_contract_status'],

        'daily_contract_dates': json.dumps(daily_contract_dates),
        'daily_contract_counts': json.dumps(daily_contract_counts),
        'status_pie_data': json.dumps(status_pie_data),
        'revenue_dates': json.dumps(revenue_dates),
        'revenue_amounts': json.dumps(revenue_amounts),
        'debt_pie_data': json.dumps(debt_pie_data),
    }
    return render(request, 'bi/contracts_payments_dashboard.html', context)

@login_required(login_url='login')
@user_passes_test
def expenses_dashboard_view(request):
    """Dashboard for Expenses statistics."""
    filters = _get_common_filters(request)
    expense_filters = filters['expense_filters']
    start_date = filters['start_date']
    end_date = filters['end_date']

    # Chart 7: Total Expenses Over Time (Line Chart)
    total_expenses_over_time = Expense.objects.filter(
        **expense_filters
    ).annotate(
        expense_date=TruncDate('created')
    ).values('expense_date').annotate(
        total_amount=Sum('amount')
    ).order_by('expense_date')
    expense_dates = [d['expense_date'].strftime('%Y-%m-%d') for d in total_expenses_over_time]
    expense_amounts = [int(d['total_amount']) for d in total_expenses_over_time]

    # Chart 8: Expenses by Type (Pie Chart)
    expenses_by_type = Expense.objects.filter(
        **expense_filters
    ).values('expense_type__name').annotate(
        total_amount=Sum('amount')
    ).order_by('-total_amount')
    expense_type_names = [d['expense_type__name'] or 'Nomalum Tur' for d in expenses_by_type]
    expense_type_amounts = [int(d['total_amount']) for d in expenses_by_type]

    all_expense_types = ExpenseType.objects.all().order_by('name')

    context = {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'all_expense_types': all_expense_types,
        'selected_expense_type_id': filters['selected_expense_type_id'],

        'expense_dates': json.dumps(expense_dates),
        'expense_amounts': json.dumps(expense_amounts),
        'expense_type_names': json.dumps(expense_type_names),
        'expense_type_amounts': json.dumps(expense_type_amounts),
    }
    return render(request, 'bi/expenses_dashboard.html', context)

@login_required
def leads_dashboard_view(request):
    """Leadlar bo'yicha statistikalar sahifasi"""

    # Default sana filtrlari
    end_date_str = request.GET.get('end_date', date.today().strftime('%Y-%m-%d'))
    start_date_str = request.GET.get('start_date', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "Noto'g'ri sana formati kiritildi.")
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
            count = next((d['count'] for d in operator_call_status_data if d['operator__full_name'] == op_name and d['call_status'] == status_code), 0)
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
    return render(request, 'bi/leads_dashboard.html', context)

