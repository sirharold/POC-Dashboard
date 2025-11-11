#!/usr/bin/env python3
"""
Test script for AvailabilityCalculator to verify weekend schedule logic.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime
import pandas as pd
from utils.availability_calculator import AvailabilityCalculator

def test_weekend_schedule():
    """Test the Weekends schedule detection."""
    print("=" * 80)
    print("Testing Weekends Schedule Logic")
    print("=" * 80)
    print("\nSchedule: Powered off from Friday 21:00 to Monday 10:00")
    print()

    # Test cases: (datetime, expected_result)
    test_cases = [
        # Regular weekday hours
        (datetime(2025, 11, 5, 12, 0), False, "Wednesday 12:00 - Should be UP"),
        (datetime(2025, 11, 6, 15, 30), False, "Thursday 15:30 - Should be UP"),

        # Friday before 21:00
        (datetime(2025, 11, 7, 20, 59), False, "Friday 20:59 - Should be UP"),

        # Friday at/after 21:00 (START of downtime)
        (datetime(2025, 11, 7, 21, 0), True, "Friday 21:00 - Should be DOWN"),
        (datetime(2025, 11, 7, 23, 59), True, "Friday 23:59 - Should be DOWN"),

        # All day Saturday
        (datetime(2025, 11, 8, 0, 0), True, "Saturday 00:00 - Should be DOWN"),
        (datetime(2025, 11, 8, 12, 0), True, "Saturday 12:00 - Should be DOWN"),
        (datetime(2025, 11, 8, 23, 59), True, "Saturday 23:59 - Should be DOWN"),

        # All day Sunday
        (datetime(2025, 11, 9, 0, 0), True, "Sunday 00:00 - Should be DOWN"),
        (datetime(2025, 11, 9, 12, 0), True, "Sunday 12:00 - Should be DOWN"),
        (datetime(2025, 11, 9, 23, 59), True, "Sunday 23:59 - Should be DOWN"),

        # Monday before 10:00
        (datetime(2025, 11, 10, 0, 0), True, "Monday 00:00 - Should be DOWN"),
        (datetime(2025, 11, 10, 9, 59), True, "Monday 09:59 - Should be DOWN"),

        # Monday at/after 10:00 (END of downtime)
        (datetime(2025, 11, 10, 10, 0), False, "Monday 10:00 - Should be UP"),
        (datetime(2025, 11, 10, 15, 0), False, "Monday 15:00 - Should be UP"),
    ]

    all_passed = True
    for dt, expected, description in test_cases:
        result = AvailabilityCalculator._is_weekend_downtime(dt)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        if result != expected:
            all_passed = False
        print(f"{status} | {description}")
        print(f"         Expected: {expected}, Got: {result}")
        print()

    print("=" * 80)
    if all_passed:
        print("✅ All tests PASSED")
    else:
        print("❌ Some tests FAILED")
    print("=" * 80)

def test_availability_calculation():
    """Test availability calculation with sample data."""
    print("\n\n" + "=" * 80)
    print("Testing Availability Calculation")
    print("=" * 80)

    # Create sample data: Friday evening through Monday morning
    # Friday 20:00 - Monday 11:00 (every hour)
    timestamps = []
    values = []

    start = datetime(2025, 11, 7, 20, 0)  # Friday 20:00

    # Generate hourly data for 3.5 days (84 hours)
    for hour in range(84):
        ts = start + pd.Timedelta(hours=hour)
        timestamps.append(ts)

        # Simulate: server goes down during scheduled weekend downtime
        # and has 2 unscheduled outages on Wednesday
        if AvailabilityCalculator._is_weekend_downtime(ts):
            values.append(0)  # Down during weekend
        else:
            values.append(1)  # Up during normal hours

    df = pd.DataFrame({
        'Timestamp': timestamps,
        'Maximum': values
    })

    print(f"\nSample data: {len(df)} datapoints from Friday 20:00 to Monday 11:00")
    print(f"Total hours: {len(df)}")

    # Calculate without schedule
    stats_no_schedule = AvailabilityCalculator.calculate_availability(df, schedule_tag=None)
    print(f"\n📊 WITHOUT considering schedule:")
    print(f"   Total points: {stats_no_schedule['total_points']}")
    print(f"   Available: {stats_no_schedule['available_points']}")
    print(f"   Unavailable: {stats_no_schedule['unavailable_points']}")
    print(f"   Availability: {stats_no_schedule['availability_percentage']:.2f}%")

    # Calculate with Weekends schedule
    stats_with_schedule = AvailabilityCalculator.calculate_availability(df, schedule_tag='Weekends')
    print(f"\n📊 WITH Weekends schedule:")
    print(f"   Total points: {stats_with_schedule['total_points']}")
    print(f"   Available: {stats_with_schedule['available_points']}")
    print(f"   Unavailable: {stats_with_schedule['unavailable_points']}")
    print(f"   Scheduled downtime points: {stats_with_schedule['scheduled_downtime_points']}")
    print(f"   Unscheduled downtime points: {stats_with_schedule['unscheduled_downtime_points']}")
    print(f"   Overall availability: {stats_with_schedule['availability_percentage']:.2f}%")
    print(f"   Scheduled availability: {stats_with_schedule['scheduled_availability_percentage']:.2f}%")

    print("\n💡 Interpretation:")
    print(f"   The server was down for {stats_with_schedule['scheduled_downtime_points']} hours during scheduled maintenance.")
    print(f"   During operational hours, it had {stats_with_schedule['scheduled_availability_percentage']:.2f}% availability.")

    print("=" * 80)

if __name__ == "__main__":
    test_weekend_schedule()
    test_availability_calculation()
