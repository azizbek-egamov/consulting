from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Max
from rest_framework.views import APIView
from rest_framework import generics, viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone
from datetime import timedelta

from .serializers import (
    LeadSerializer,
    OperatorSerializer,
    LeadStageSerializer,
    ClientInformationSerializer,
    ConsultingContractSerializer,
)
from main.models import (
    Lead,
    CallOperator,
    LeadStage,
    ClientInformation,
    ConsultingContract,
)


class LeadStageApi(generics.ListAPIView):
    queryset = LeadStage.objects.all()
    serializer_class = LeadStageSerializer

class OperatorListApi(generics.ListAPIView):
    queryset = CallOperator.objects.all()
    serializer_class = OperatorSerializer

class OperatorCreateApi(generics.CreateAPIView):
    queryset = CallOperator.objects.all()
    serializer_class = OperatorSerializer

class OperatorApi(generics.RetrieveUpdateDestroyAPIView):
    queryset = CallOperator.objects.all()
    serializer_class = OperatorSerializer
    lookup_field = 'id'

class LeadApi(APIView):
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'operator',
                openapi.IN_QUERY,
                description="Operator ID",
                type=openapi.TYPE_INTEGER
            )
        ]
    )
    def get(self, request, pk=None):
        operator_id = request.GET.get('operator')
        
        if pk:
            item = get_object_or_404(Lead, pk=pk)
            serializer = LeadSerializer(item)
        else:
            queryset = Lead.objects.all()
            if operator_id:
                queryset = queryset.filter(operator=operator_id)
            serializer = LeadSerializer(queryset, many=True)
        
        return Response(serializer.data)

    @swagger_auto_schema(request_body=LeadSerializer)
    def post(self, request):
        serializer = LeadSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    
class LealDetailApi(APIView):

    def get_object(self, pk):
        return get_object_or_404(Lead, pk=pk)

    def get(self, request, pk):
        product = self.get_object(pk)
        serializer = LeadSerializer(product)
        return Response(serializer.data)

    def put(self, request, pk):
        item = get_object_or_404(Lead, pk=pk)
        serializer = LeadSerializer(item, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        item = get_object_or_404(Lead, pk=pk)
        serializer = LeadSerializer(item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        item = get_object_or_404(Lead, pk=pk)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientInformationSerializer
    queryset = ClientInformation.objects.all().order_by('-created')
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('heard', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Eshitgan manba (contains)"),
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="F.I.Sh/telefon/passport qidiruv"),
        ]
    )
    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        heard = request.query_params.get('heard')
        search = request.query_params.get('search')
        if heard:
            qs = qs.filter(heard__icontains=heard)
        if search:
            qs = qs.filter(
                Q(full_name__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(middle_name__icontains=search) |
                Q(phone__icontains=search) |
                Q(phone2__icontains=search) |
                Q(passport_number__icontains=search)
            )
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class ConsultingContractViewSet(viewsets.ModelViewSet):
    serializer_class = ConsultingContractSerializer
    queryset = ConsultingContract.objects.all().select_related('client').prefetch_related('family_members').order_by('-created_at')
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Status: draft/preparation/submitted/completed/cancelled"),
            openapi.Parameter('heard', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Mijoz eshitgan manba (contains)"),
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Mijoz F.I.Sh / telefon / passport bo'yicha qidiruv"),
        ]
    )
    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        status_param = request.query_params.get('status')
        heard = request.query_params.get('heard')
        search = request.query_params.get('search')

        if status_param:
            qs = qs.filter(status=status_param)
        if heard:
            qs = qs.filter(Q(client__heard__icontains=heard))
        if search:
            qs = qs.filter(
                Q(client__full_name__icontains=search) |
                Q(client__first_name__icontains=search) |
                Q(client__last_name__icontains=search) |
                Q(client__middle_name__icontains=search) |
                Q(client__phone__icontains=search) |
                Q(client__phone2__icontains=search) |
                Q(passport_number__icontains=search)
            )

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)