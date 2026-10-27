
import pytest
from datetime import date
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from clean import parse_amount, parse_date, clean_domain

def test_parse_amount():
    assert parse_amount("PKR 18,500.00") == 18500.00
    assert parse_amount("(1,500)") == -1500.00

def test_parse_date():
    assert parse_date("2026-08-03") == date(2026, 8, 3)

def test_clean_domain():
    assert clean_domain("http://www.pkhosting.com..") == "pkhosting.com"