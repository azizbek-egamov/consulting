import base64
import json
import logging
import os
import random
from datetime import datetime, date
from uuid import uuid4

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils.text import slugify
from rest_framework import serializers

from main import models

# Set up logging
logger = logging.getLogger(__name__)

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
            "birth_date",
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
    contract_number = serializers.IntegerField(read_only=True)
    contract_date = serializers.DateField(
        format="%Y-%m-%d",
        input_formats=["%Y-%m-%d", "%d.%m.%Y"],
        required=False,
        allow_null=True,
    )
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

    def to_representation(self, instance):
        if isinstance(getattr(instance, "contract_date", None), datetime):
            instance.contract_date = instance.contract_date.date()

        def _normalize_media(val):
            if not val:
                return ""
            s = str(val).replace("\\", "/")
            if s.startswith("http"):
                return s
            s = s.lstrip("/")
            if s.startswith("media/"):
                s = s[6:]
            return f"/media/{s}"

        data = super().to_representation(instance)
        for key in ["passport_images", "visa_images", "completed_contract_images"]:
            if key in data and isinstance(data[key], list):
                data[key] = [_normalize_media(x) for x in data[key] if x]
        return data

    def _save_base64_image(self, base64_str, file_name, prefix):
        """Save base64 image data to a file and return the relative path.
        
        Args:
            base64_str: Base64 encoded image string (with or without data URL prefix)
            file_name: File name (should already contain client name, e.g., "egamov-azizbek_1")
            prefix: Directory prefix (e.g., "passport_image", "visa_image", "completed_contract_image")
        """
        if not base64_str or not isinstance(base64_str, str):
            return None
            
        # Handle data URL format
        if ';base64,' in base64_str:
            # Extract the data and content type
            content_type, imgstr = base64_str.split(';base64,')
            # Get file extension from content type (e.g., 'image/png' -> 'png')
            ext = content_type.split('/')[-1] if '/' in content_type else 'bin'
            # Remove any parameters from content type (e.g., 'image/png;charset=UTF-8')
            if ';' in ext:
                ext = ext.split(';')[0]
        else:
            # If no data URL prefix, assume it's a raw base64 string
            imgstr = base64_str
            ext = 'bin'  # Default extension for unknown binary data
            
        try:
            # Decode the base64 string
            data = base64.b64decode(imgstr)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.join('media', prefix), exist_ok=True)
            
            # Generate a safe filename with proper extension
            safe_ext = f".{ext}" if not ext.startswith('.') and ext != 'jpeg' else f".{ext}"
            # Handle common image extensions
            if safe_ext == '.jpeg':
                safe_ext = '.jpg'
            elif safe_ext not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                safe_ext = '.jpg'  # Default to jpg for unknown image types
            
            # file_name already contains client name (e.g., "egamov-azizbek" or "egamov-azizbek_1")
            # Just add extension, no need for UUID since client name is unique enough
            final_file_name = f"{prefix}/{file_name}{safe_ext}"
            
            # Use direct file write to avoid Django's auto-unique naming
            from django.conf import settings
            media_root = settings.MEDIA_ROOT
            exact_path = os.path.join(media_root, final_file_name)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(exact_path), exist_ok=True)
            
            # If file already exists, delete it first
            if os.path.exists(exact_path):
                try:
                    os.remove(exact_path)
                except Exception as e:
                    logger.warning(f"Could not delete existing file {exact_path}: {str(e)}")
            
            # Write file directly with exact filename
            with open(exact_path, 'wb') as f:
                f.write(data)
            
            # Return the relative URL path
            full_path = final_file_name
            if full_path.startswith("media/"):
                return f"/{full_path}"
            return f"/media/{full_path}"
            
        except Exception as e:
            logger.error(f"Error saving base64 image: {str(e)}")
            return None

    def _handle_files(self, files, prefix, limit, contract_number, client_name):
        """Handle file uploads (both regular files and base64 strings).
        
        Args:
            files: List of files (can be file objects or base64 strings)
            prefix: Directory prefix (e.g., "passport_image", "visa_image", "completed_contract_image")
            limit: Maximum number of files allowed
            contract_number: Contract number (for reference, not used in filename)
            client_name: Client full name (e.g., "Egamov Azizbek")
        
        Filename rules:
        - passport_image: egamov-azizbek.jpg (no counter, no random)
        - visa_image: egamov-azizbek_1234567.jpg (with 6-7 digit random)
        - completed_contract_image: egamov-azizbek_1234567.jpg (with 6-7 digit random, multiple files)
        """
        stored = []
        media_url = "media"
        
        # Validate client_name - it's required for proper filenames
        if not client_name or not client_name.strip():
            raise serializers.ValidationError(
                {prefix: "Mijoz ismi kiritilmagan. Rasm saqlash uchun mijoz ismi zarur."}
            )
        
        # Slugify client name to create safe filename (e.g., "Egamov Azizbek" -> "egamov-azizbek")
        base_prefix = slugify(client_name)
        if not base_prefix:
            raise serializers.ValidationError(
                {prefix: "Mijoz ismi noto'g'ri formatda. Rasm saqlash uchun to'g'ri mijoz ismi zarur."}
            )
        
        # Determine filename format based on prefix
        is_passport = prefix == "passport_image"
        is_visa = prefix == "visa_image"
        is_completed = prefix == "completed_contract_image"
        
        counter = 1
        for f in files:
            # Generate random number (6-7 digits) for visa and completed_contract images
            random_suffix = None
            if is_visa or is_completed:
                random_suffix = random.randint(100000, 9999999)  # 6-7 digit random number
            
            # Handle file uploads
            if hasattr(f, 'read'):  # This is a file upload
                ext = os.path.splitext(f.name)[1] or '.jpg'
                
                # Build filename based on type
                if is_passport:
                    # Passport: egamov-azizbek.jpg (no suffix)
                    fname = f"{prefix}/{base_prefix}{ext}"
                elif is_visa:
                    # Visa: egamov-azizbek_1234567.jpg (with random)
                    fname = f"{prefix}/{base_prefix}_{random_suffix}{ext}"
                elif is_completed:
                    # Completed contract: egamov-azizbek_1234567.jpg (with random for each)
                    fname = f"{prefix}/{base_prefix}_{random_suffix}{ext}"
                else:
                    # Fallback
                    fname = f"{prefix}/{base_prefix}{ext}"
                
                # Use direct file write to avoid Django's auto-unique naming
                from django.conf import settings
                media_root = settings.MEDIA_ROOT
                exact_path = os.path.join(media_root, fname)
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(exact_path), exist_ok=True)
                
                # If file already exists, delete it first
                if os.path.exists(exact_path):
                    try:
                        os.remove(exact_path)
                    except Exception as e:
                        logger.warning(f"Could not delete existing file {exact_path}: {str(e)}")
                
                # Write file directly with exact filename
                # Read file content first (reset pointer if needed)
                f.seek(0)
                file_content = f.read()
                with open(exact_path, 'wb') as file_obj:
                    file_obj.write(file_content)
                
                path = fname
                counter += 1
            # Handle base64 strings
            elif isinstance(f, str) and (f.startswith('data:image/') or len(f) > 100):
                # Build filename based on type
                if is_passport:
                    # Passport: "egamov-azizbek" (no suffix)
                    file_name = base_prefix
                elif is_visa:
                    # Visa: "egamov-azizbek_1234567" (with random)
                    file_name = f"{base_prefix}_{random_suffix}"
                elif is_completed:
                    # Completed contract: "egamov-azizbek_1234567" (with random for each)
                    file_name = f"{base_prefix}_{random_suffix}"
                else:
                    # Fallback
                    file_name = base_prefix
                
                path = self._save_base64_image(f, file_name, prefix)
                if path:
                    counter += 1
                else:
                    continue
            else:
                continue
                
            # Format the path correctly
            if path.startswith("media/"):
                path = path[6:]
            elif path.startswith("/media/"):
                path = path[7:]
                
            full_path = f"/{media_url}/{path}" if not path.startswith("/") else path
            stored.append(full_path)
            
        if len(stored) > limit:
            raise serializers.ValidationError(
                {prefix: f"Maksimal {limit} ta rasm yuklash mumkin."}
            )
        return stored

    def _extract_files(self, request, key):
        """Extract files from request - either file uploads OR base64 strings, not both.
        
        Priority:
        1. If there are file uploads in request.FILES, use those
        2. Otherwise, check request.data for base64 strings
        3. Don't mix file uploads and base64 strings
        """
        if not request:
            return []
        
        files = []
        
        # First, check for regular file uploads
        file_uploads = request.FILES.getlist(key, [])
        if file_uploads:
            # If we have file uploads, use only those (ignore base64 in request.data)
            files.extend(file_uploads)
        else:
            # If no file uploads, check for base64 data in request.data
            if request.data and key in request.data:
                data = request.data[key]
                if isinstance(data, str):
                    # Check if it's a base64 string (long string or data URL)
                    if data.startswith('data:image/') or len(data) > 100:
                        files.append(data)
                elif isinstance(data, list):
                    # Filter only base64 strings (long strings or data URLs)
                    for item in data:
                        if isinstance(item, str) and (item.startswith('data:image/') or len(item) > 100):
                            files.append(item)
                
        return files

    def _get_client_name(self, client_data):
        parts = [client_data.get("last_name", ""), client_data.get("first_name", "")]
        if client_data.get("middle_name"):
            parts.append(client_data["middle_name"])
        return " ".join([p for p in parts if p]).strip()

    def _validate_images(self, instance, validated_data, request, client_data=None):
        contract_number = validated_data.get("contract_number") or getattr(
            instance, "contract_number", None
        )
        # Get client_name from client_data if provided, otherwise from validated_data
        if client_data is None:
            client_data = validated_data.get("client", {})
        # If client_data is still empty, try to get from instance
        if not client_data and instance:
            client_data = {
                "last_name": getattr(instance.client, "last_name", "") if instance.client else "",
                "first_name": getattr(instance.client, "first_name", "") if instance.client else "",
                "middle_name": getattr(instance.client, "middle_name", "") if instance.client else "",
            }
        client_name = self._get_client_name(client_data)

        # Get existing images from instance (if updating) or empty list (if creating)
        existing_passport = (instance.passport_images if instance else []) or []
        existing_completed = (instance.completed_contract_images if instance else []) or []
        existing_visa = (instance.visa_images if instance else []) or []

        # Remove passport_images, completed_contract_images, visa_images from validated_data
        # to prevent them from being saved directly (we'll handle them separately)
        validated_data.pop("passport_images", None)
        validated_data.pop("completed_contract_images", None)
        validated_data.pop("visa_images", None)

        # Extract new files from request (either file uploads or base64 strings)
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

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get("request")

        # JSON string bo'lishi mumkin
        client_data = validated_data.pop("client", None)
        if isinstance(client_data, str):
            try:
                client_data = json.loads(client_data)
            except json.JSONDecodeError:
                raise serializers.ValidationError({"client": "Invalid JSON"})

        family_members_data = validated_data.pop("family_members", [])
        if isinstance(family_members_data, str):
            try:
                family_members_data = json.loads(family_members_data)
            except json.JSONDecodeError:
                family_members_data = []

        # contract_number avtomatik
        if not validated_data.get("contract_number"):
            max_num = models.ConsultingContract.objects.aggregate(
                max_num=models.Max("contract_number")
            )["max_num"] or 0
            validated_data["contract_number"] = max_num + 1

        passport_images, completed_images, visa_images = self._validate_images(
            None, validated_data, request, client_data
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

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get("request")

        client_data = validated_data.pop("client", None)
        if isinstance(client_data, str):
            try:
                client_data = json.loads(client_data)
            except json.JSONDecodeError:
                raise serializers.ValidationError({"client": "Invalid JSON"})

        family_members_data = validated_data.pop("family_members", None)
        if isinstance(family_members_data, str):
            try:
                family_members_data = json.loads(family_members_data)
            except json.JSONDecodeError:
                family_members_data = []

        passport_images, completed_images, visa_images = self._validate_images(
            instance, validated_data, request, client_data
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