import pytest
from backend.utils import format_duration

def test_format_duration():
    # Null or None cases
    assert format_duration(None) == "N/A"
    
    # 0 seconds
    assert format_duration(0) == "0 minutes"
    assert format_duration(-10) == "0 minutes"
    
    # Minutes only
    assert format_duration(120) == "2 minutes"
    assert format_duration(65) == "1 minute"
    
    # Hours and minutes
    assert format_duration(3660) == "1 hour, 1 minute"
    assert format_duration(7200) == "2 hours, 0 minutes"
    
    # Days, hours, minutes
    assert format_duration(90000) == "1 day, 1 hour, 0 minutes"
    assert format_duration(176400) == "2 days, 1 hour, 0 minutes"
