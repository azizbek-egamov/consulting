import os
import django
from aiogram import Router, F, Bot, types
from aiogram.filters import StateFilter, CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from asgiref.sync import sync_to_async
from datetime import datetime, timedelta
import tempfile
import re
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
import asyncio

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from main.models import *
from django.db.models import IntegerField
from django.db.models.functions import Cast

router = Router()