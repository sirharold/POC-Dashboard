"""
Availability Calculator - Handles availability percentage calculations considering schedules.
"""
from datetime import datetime, time, timedelta
import pandas as pd


class AvailabilityCalculator:
    """Calculate availability percentages considering scheduled downtimes."""

    SCHEDULES = {
        'Weekends': {
            'description': 'Powered off from Friday 21:00 to Monday 10:00',
            'is_scheduled_downtime': lambda dt: AvailabilityCalculator._is_weekend_downtime(dt)
        },
        'Nights': {
            'description': 'Powered off from 21:00 to 06:00 daily',
            'is_scheduled_downtime': lambda dt: AvailabilityCalculator._is_night_downtime(dt)
        },
        'BusinessHours': {
            'description': 'Only available Monday-Friday 08:00-18:00',
            'is_scheduled_downtime': lambda dt: AvailabilityCalculator._is_outside_business_hours(dt)
        },
        'Weekdays': {
            'description': 'Only available Monday-Friday 10:00-21:00 Chile time (since Nov 6, 2024)',
            'is_scheduled_downtime': lambda dt: AvailabilityCalculator._is_weekdays_downtime(dt)
        }
    }

    @staticmethod
    def _is_weekend_downtime(dt: datetime) -> bool:
        """
        Check if datetime is within weekend downtime (Friday 21:00 to Monday 10:00).

        Args:
            dt: datetime to check

        Returns:
            True if within scheduled weekend downtime
        """
        weekday = dt.weekday()  # Monday=0, Sunday=6
        hour = dt.hour

        # Friday after 21:00
        if weekday == 4 and hour >= 21:
            return True

        # Saturday (all day)
        if weekday == 5:
            return True

        # Sunday (all day)
        if weekday == 6:
            return True

        # Monday before 10:00
        if weekday == 0 and hour < 10:
            return True

        return False

    @staticmethod
    def _is_night_downtime(dt: datetime) -> bool:
        """
        Check if datetime is within nightly downtime (21:00 to 06:00).

        Args:
            dt: datetime to check

        Returns:
            True if within scheduled nightly downtime
        """
        hour = dt.hour
        return hour >= 21 or hour < 6

    @staticmethod
    def _is_outside_business_hours(dt: datetime) -> bool:
        """
        Check if datetime is outside business hours (Monday-Friday 08:00-18:00).

        Args:
            dt: datetime to check

        Returns:
            True if outside business hours
        """
        weekday = dt.weekday()
        hour = dt.hour

        # Weekend
        if weekday >= 5:
            return True

        # Outside 08:00-18:00
        if hour < 8 or hour >= 18:
            return True

        return False

    @staticmethod
    def _is_weekdays_downtime(dt: datetime) -> bool:
        """
        Check if datetime is outside weekdays operating hours (Monday-Friday 10:00-21:00 Chile time).
        This schedule only applies from November 6, 2024 onwards.

        Args:
            dt: datetime to check

        Returns:
            True if outside scheduled weekdays operating hours
        """
        # Only apply this schedule from November 6, 2024
        cutoff_date = datetime(2024, 11, 6)
        if dt < cutoff_date:
            return False

        weekday = dt.weekday()  # Monday=0, Sunday=6
        hour = dt.hour

        # Weekend (Saturday or Sunday)
        if weekday >= 5:
            return True

        # Weekday but outside 10:00-21:00
        if hour < 10 or hour >= 21:
            return True

        return False

    @staticmethod
    def calculate_availability(df: pd.DataFrame, schedule_tag: str = None,
                              value_column: str = 'Maximum') -> dict:
        """
        Calculate availability percentage from ping data, considering schedule.

        Args:
            df: DataFrame with 'Timestamp' and value columns (0 or 1)
            schedule_tag: Schedule tag value (e.g., 'Weekends', 'Nights', 'BusinessHours')
            value_column: Column name containing the metric value (default: 'Maximum')

        Returns:
            Dictionary with:
                - total_points: Total datapoints
                - available_points: Points where value == 1
                - unavailable_points: Points where value == 0
                - scheduled_downtime_points: Points during scheduled downtime
                - unscheduled_downtime_points: Points unavailable outside schedule
                - availability_percentage: Overall availability %
                - scheduled_availability_percentage: Availability excluding scheduled downtime %
        """
        if df.empty:
            return {
                'total_points': 0,
                'available_points': 0,
                'unavailable_points': 0,
                'scheduled_downtime_points': 0,
                'unscheduled_downtime_points': 0,
                'availability_percentage': 0.0,
                'scheduled_availability_percentage': 0.0
            }

        total_points = len(df)
        available_points = len(df[df[value_column] == 1])
        unavailable_points = len(df[df[value_column] == 0])

        # Calculate overall availability
        availability_percentage = (available_points / total_points * 100) if total_points > 0 else 0

        # If no schedule, return basic calculation
        if not schedule_tag or schedule_tag not in AvailabilityCalculator.SCHEDULES:
            return {
                'total_points': total_points,
                'available_points': available_points,
                'unavailable_points': unavailable_points,
                'scheduled_downtime_points': 0,
                'unscheduled_downtime_points': unavailable_points,
                'availability_percentage': availability_percentage,
                'scheduled_availability_percentage': availability_percentage
            }

        # Get schedule checker function
        schedule_config = AvailabilityCalculator.SCHEDULES[schedule_tag]
        is_scheduled_downtime = schedule_config['is_scheduled_downtime']

        # Identify scheduled downtime points
        df_copy = df.copy()
        df_copy['is_scheduled_downtime'] = df_copy['Timestamp'].apply(
            lambda ts: is_scheduled_downtime(ts.to_pydatetime() if hasattr(ts, 'to_pydatetime') else ts)
        )

        # Count scheduled downtime points
        scheduled_downtime_points = len(df_copy[df_copy['is_scheduled_downtime'] == True])

        # Count unavailable points during scheduled downtime
        unavailable_during_scheduled = len(df_copy[
            (df_copy['is_scheduled_downtime'] == True) & (df_copy[value_column] == 0)
        ])

        # Unscheduled downtime = unavailable points outside scheduled downtime
        unscheduled_downtime_points = unavailable_points - unavailable_during_scheduled

        # Calculate availability excluding scheduled downtime periods
        non_scheduled_points = total_points - scheduled_downtime_points
        available_during_non_scheduled = len(df_copy[
            (df_copy['is_scheduled_downtime'] == False) & (df_copy[value_column] == 1)
        ])

        scheduled_availability_percentage = (
            (available_during_non_scheduled / non_scheduled_points * 100)
            if non_scheduled_points > 0 else 0
        )

        return {
            'total_points': total_points,
            'available_points': available_points,
            'unavailable_points': unavailable_points,
            'scheduled_downtime_points': scheduled_downtime_points,
            'unscheduled_downtime_points': unscheduled_downtime_points,
            'availability_percentage': availability_percentage,
            'scheduled_availability_percentage': scheduled_availability_percentage
        }

    @staticmethod
    def get_schedule_description(schedule_tag: str) -> str:
        """
        Get human-readable description of a schedule.

        Args:
            schedule_tag: Schedule tag value

        Returns:
            Description string, or empty string if schedule not found
        """
        if schedule_tag in AvailabilityCalculator.SCHEDULES:
            return AvailabilityCalculator.SCHEDULES[schedule_tag]['description']
        return ""
