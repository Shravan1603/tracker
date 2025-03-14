from datetime import datetime, timedelta

def create_time_slots(start_time, end_time, duration_minutes, recurring_days=None):
    """
    Generate time slots between start_time and end_time with specified duration.
    Supports optional recurring weekly days.
    """
    slots = []
    current_time = datetime.strptime(start_time, "%H:%M")
    end_time = datetime.strptime(end_time, "%H:%M")

    # Generate slots for a single day
    while current_time + timedelta(minutes=duration_minutes) <= end_time:
        slot = f"{current_time.strftime('%H:%M')} - {(current_time + timedelta(minutes=duration_minutes)).strftime('%H:%M')}"
        slots.append(slot)
        current_time += timedelta(minutes=duration_minutes)

    # Handle recurring days
    if recurring_days:
        full_schedule = []
        for day in recurring_days:
            full_schedule.extend([f"{day} {slot}" for slot in slots])
        return full_schedule
    
    return slots


def is_slot_available(existing_slots, new_slot):
    """
    Check if the new slot conflicts with any existing slots.
    """
    new_start, new_end = [datetime.strptime(t.strip(), "%H:%M") for t in new_slot.split("-")]
    
    for slot in existing_slots:
        start, end = [datetime.strptime(t.strip(), "%H:%M") for t in slot.split("-")]
        if (start < new_end and new_start < end):
            return False  # Overlap detected

    return True


# Example usage
start_time = "09:00"
end_time = "18:00"
duration = 30
recurring_days = ["Monday", "Wednesday", "Friday"]

slots = create_time_slots(start_time, end_time, duration, recurring_days)

# Example: Add a new slot and check for conflicts
new_slot = "10:30 - 11:00"
if is_slot_available(slots, new_slot):
    slots.append(new_slot)
    print("New slot added!")
else:
    print("Time slot conflict detected!")

print("Generated Time Slots:", slots)
