from rest_framework import serializers
from main import models
from django.utils.text import slugify
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import os
from uuid import uuid4
import json

class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Lead
        fields = "__all__"
        
class OperatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CallOperator
        fields = "__all__"
        
class LeadStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.LeadStage
        fields = ['id', 'name', 'key', 'is_system_stage']


class ClientInformationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ClientInformation
        fields = [
            "id",
            "first_name",
            "last_name",
            "middle_name",
            "full_name",
            "phone",
            "phone2",
            "passport_number",
            "passport_issue_date",
            "passport_expiry_date",
            "passport_issue_place",
            "address",
            "email",
            "password",
            "heard",
            "created",
        ]
        read_only_fields = ["id", "full_name", "created"]

    def create(self, validated_data):
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class ContractFamilyMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ContractFamilyMember
        fields = [
            "id",
            "first_name",
            "last_name",
            "middle_name",
            "full_name",
            "relationship",
            "passport_number",
            "passport_issue_date",
            "passport_expiry_date",
            "passport_issue_place",
            "birth_date",
            "phone",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "full_name", "created_at", "updated_at"]


class ConsultingContractSerializer(serializers.ModelSerializer):
    client = ClientInformationSerializer()
    family_members = ContractFamilyMemberSerializer(many=True, required=False)
    passport_images = serializers.ListField(
        child=serializers.CharField(), required=False, allow_null=True
    )
    completed_contract_images = serializers.ListField(
        child=serializers.CharField(), required=False, allow_null=True
    )
    visa_images = serializers.ListField(
        child=serializers.CharField(), required=False, allow_null=True
    )

    class Meta:
        model = models.ConsultingContract
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "remaining_amount"]

    def _handle_files(self, files, prefix, limit, contract_number, client_name):
        stored = []
        media_url = "media"
        name_parts = []
        if client_name:
            name_parts.append(slugify(client_name))
        base_prefix = "-".join([p for p in name_parts if p]) or prefix

        for f in files:
            ext = os.path.splitext(f.name)[1]
            fname = f"{prefix}/{base_prefix}{ext}"
            path = default_storage.save(fname, ContentFile(f.read()))
            if path.startswith("media/"):
                path = path[6:]
            elif path.startswith("/media/"):
                path = path[7:]
            if not path.startswith("/media/"):
                full_path = f"/{media_url}/{path}" if media_url else f"/{path}"
            else:
                full_path = path
            stored.append(full_path)
        if len(stored) > limit:
            raise serializers.ValidationError(
                {prefix: f"Maksimal {limit} ta rasm yuklash mumkin."}
            )
        return stored

    def _extract_files(self, request, key):
        if not request:
            return []
        return request.FILES.getlist(key)

    def _get_client_name(self, client_data):
        parts = [client_data.get("last_name", ""), client_data.get("first_name", "")]
        if client_data.get("middle_name"):
            parts.append(client_data["middle_name"])
        return " ".join([p for p in parts if p]).strip()

    def _validate_images(self, instance, validated_data, request):
        contract_number = validated_data.get("contract_number") or getattr(
            instance, "contract_number", None
        )
        client_name = self._get_client_name(validated_data.get("client", {}))

        existing_passport = (
            validated_data.pop("passport_images", None)
            if "passport_images" in validated_data
            else (instance.passport_images if instance else [])
        ) or []
        existing_completed = (
            validated_data.pop("completed_contract_images", None)
            if "completed_contract_images" in validated_data
            else (instance.completed_contract_images if instance else [])
        ) or []
        existing_visa = (
            validated_data.pop("visa_images", None)
            if "visa_images" in validated_data
            else (instance.visa_images if instance else [])
        ) or []

        new_passport_files = self._extract_files(request, "passport_images")
        new_completed_files = self._extract_files(request, "completed_contract_images")
        new_visa_files = self._extract_files(request, "visa_images")

        passport_uploaded = self._handle_files(
            new_passport_files, "passport_image", 1, contract_number, client_name
        )
        completed_uploaded = self._handle_files(
            new_completed_files, "completed_contract_image", 3, contract_number, client_name
        )
        visa_uploaded = self._handle_files(
            new_visa_files, "visa_image", 1, contract_number, client_name
        )

        passport_total = existing_passport + passport_uploaded
        completed_total = existing_completed + completed_uploaded
        visa_total = existing_visa + visa_uploaded

        if len(passport_total) > 2:
            raise serializers.ValidationError(
                {"passport_images": "Maksimal 2 ta rasmga ruxsat."}
            )
        if len(completed_total) > 3:
            raise serializers.ValidationError(
                {"completed_contract_images": "Maksimal 3 ta rasmga ruxsat."}
            )
        if len(visa_total) > 1:
            raise serializers.ValidationError(
                {"visa_images": "Maksimal 1 ta VISA rasmi yuklash mumkin."}
            )

        return passport_total, completed_total, visa_total

    def create(self, validated_data):
        request = self.context.get("request")
        client_data = validated_data.pop("client")
        family_members_data = validated_data.pop("family_members", [])
        if isinstance(family_members_data, str):
            try:
                family_members_data = json.loads(family_members_data) or []
            except json.JSONDecodeError:
                family_members_data = []

        contract_number = validated_data.get("contract_number")
        if not contract_number:
            max_num = models.ConsultingContract.objects.aggregate(max_num=models.Max("contract_number"))[
                "max_num"
            ] or 0
            validated_data["contract_number"] = max_num + 1

        passport_images, completed_images, visa_images = self._validate_images(
            None, validated_data, request
        )

        client_serializer = ClientInformationSerializer(data=client_data)
        client_serializer.is_valid(raise_exception=True)
        client = client_serializer.save()

        contract = models.ConsultingContract.objects.create(
            client=client,
            passport_images=passport_images,
            completed_contract_images=completed_images,
            visa_images=visa_images,
            **validated_data,
        )

        for fm in family_members_data:
            fm_serializer = ContractFamilyMemberSerializer(data=fm)
            fm_serializer.is_valid(raise_exception=True)
            fm_serializer.save(contract=contract)

        return contract

    def update(self, instance, validated_data):
        request = self.context.get("request")
        client_data = validated_data.pop("client", None)
        family_members_data = validated_data.pop("family_members", None)
        if isinstance(family_members_data, str):
            try:
                family_members_data = json.loads(family_members_data) or []
            except json.JSONDecodeError:
                family_members_data = []

        passport_images, completed_images, visa_images = self._validate_images(
            instance, validated_data, request
        )

        if client_data:
            client_serializer = ClientInformationSerializer(
                instance.client, data=client_data, partial=True
            )
            client_serializer.is_valid(raise_exception=True)
            client_serializer.save()

        instance.passport_images = passport_images
        instance.completed_contract_images = completed_images
        instance.visa_images = visa_images

        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()

        if family_members_data is not None:
            instance.family_members.all().delete()
            for fm in family_members_data:
                fm_serializer = ContractFamilyMemberSerializer(data=fm)
                fm_serializer.is_valid(raise_exception=True)
                fm_serializer.save(contract=instance)

        return instance