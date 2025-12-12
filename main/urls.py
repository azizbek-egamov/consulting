"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from main.views import *
from main import leads_views, bi_views, user_views

urlpatterns = [
    path("", HomePage, name="home"),
    
    path("login/", LoginPage, name="login"),
    path("logout/", LogoutPage, name="logout"),
    

    path("client/", ClientPage, name="client"),
    path("client/create/", ClientCreate, name="client-create"),
    path("client/delete/<int:id>/", ClientDelete, name="client-delete"),
    path("client/edit/<int:id>/", ClientEdit, name="client-edit"),
    path('client/export/', ClientDownload, name="export-client"),
    path('client/export/excel/', ClientDownloadExcel, name="export-client-excel"),

    path("contract/", ContractPage, name="contract"),
    path("contract/create/", ContractCreate, name="contract-create"),
    path("contract/edit/<int:id>/", ContractEdit, name="contract-edit"),
    path("contract/delete/<int:id>/", ContractDelete, name="contract-delete"),
    path("contract/<int:id>/", ContractCreatePDF, name="contract-pdf"),
    path("contract/<int:id>/details/", ContractDetailsAPI, name="contract-details-api"),
    
    # path("notifications/", NotificationsPage, name="notifications"),
    
    path('leads/', leads_views.leads_kanban, name='leads_kanban'),
    path('leads/list/', leads_views.leads_list, name='leads_list'),
    path('leads/create/', leads_views.lead_create, name='lead_create'),
    path('leads/<int:lead_id>/edit/', leads_views.lead_edit, name='lead_edit'),
    path('leads/<int:lead_id>/detail/', leads_views.lead_detail, name='lead_detail'),
    path('leads/<int:lead_id>/delete/', leads_views.lead_delete, name='lead_delete'),
    path('leads/<int:lead_id>/convert/', leads_views.lead_convert_to_client, name='lead_convert_to_client'),
    path('leads/dashboard/', leads_views.leads_dashboard, name='leads_dashboard'),
    path('leads/quick-create/', leads_views.lead_quick_create, name='lead_quick_create'),
    path('leads/update-stage/', leads_views.update_lead_stage, name='update_lead_stage'),
    path('leads/update-stage-order/', leads_views.update_stage_order, name='update_stage_order'), # Bu endi ishlatilmaydi
    path('leads/stages/create/', leads_views.create_lead_stage, name='create_lead_stage'),
    path('leads/stages/edit/<int:stage_id>/', leads_views.edit_lead_stage, name='edit_lead_stage'),
    path('leads/stages/delete/<int:stage_id>/', leads_views.delete_lead_stage, name='delete_lead_stage'),
    path('leads/statistics/', leads_views.leads_statistics_view, name='leads_statistics'),
    
    # path('bi/', bi_views.bi_dashboard_view, name='bi_dashboard'),
    path('bi/contracts-payments/', bi_views.contracts_payments_dashboard_view, name='bi_contracts_payments'),
    path('bi/leads/', bi_views.leads_dashboard_view, name='bi_leads'),
    path('bi/users/', bi_views.users_dashboard_view, name='bi_users'),
    
    # User management (ceoadmin only)
    path('users/', user_views.UserManagementPage, name='user-management'),
    path('users/create/', user_views.UserCreate, name='user-create'),
    path('users/edit/<int:id>/', user_views.UserEdit, name='user-edit'),
    path('users/change-password/<int:id>/', user_views.UserChangePassword, name='user-change-password'),
    path('users/delete/<int:id>/', user_views.UserDelete, name='user-delete'),
]
