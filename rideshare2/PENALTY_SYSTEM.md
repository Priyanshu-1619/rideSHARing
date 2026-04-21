# Penalty System Documentation

## Overview
A comprehensive penalty system has been added to the NextRide application to enforce accountability and maintain service quality. Penalties are applied automatically for various infractions including cancellations, delays, and missed rides.

## Penalty Types & Amounts

### 1. **Rider Cancellation** - ₹100
- Applied when a rider cancels an **already-accepted** booking
- Deters last-minute cancellations
- Only applies if request status is 'Accepted'

### 2. **Driver Cancellation** - ₹200
- Applied to all riders in an accepted ride when the driver cancels
- Higher penalty to encourage drivers to honor commitments
- Applied to each rider affected by the cancellation

### 3. **Delay Penalty** - ₹2 per minute (Capped at ₹100)
- Applied when driver arrives more than 5 minutes late
- Calculated as: `min(delay_minutes × 2, 100)`
- Example: 30-minute delay = ₹60 penalty
- Grace period: First 5 minutes are free

### 4. **Missed Ride (No-Show)** - ₹150
- Applied when a rider doesn't show up for an accepted ride
- Driver can mark rider as "no-show"
- Automatic penalty assessment

## Database Schema Changes

### New Table: `Penalties`
```sql
CREATE TABLE Penalties (
    penalty_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    request_id INT NOT NULL,
    penalty_type ENUM('Cancellation','Delay','Missed-Ride','Driver-Cancellation') NOT NULL,
    amount DECIMAL(8,2) NOT NULL,
    reason TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES Students(student_id),
    FOREIGN KEY (request_id) REFERENCES Requests(request_id)
);
```

### Updated `Requests` Table - New Columns
- `actual_arrival_time` - When the ride actually completed
- `completion_status` - Enum: 'On-Time', 'Late', 'Missed', 'Cancelled', 'Driver-Cancelled'

### Updated `Requests` Table - New Status Values
- 'Completed' - Ride completed successfully
- 'No-Show' - Rider didn't show up
- 'Late' - Ride completed but late

## API Endpoints

### 1. **Complete a Ride** (Driver)
```
PATCH /api/rides/<ride_id>/complete
Content-Type: application/json

{
    "actual_arrival_time": "2024-04-20T15:45:00"
}

Response:
{
    "message": "Ride completed",
    "penalty_count": 2,
    "penalties": [
        {
            "request_id": 5,
            "penalty": "Delay",
            "amount": 60
        }
    ]
}
```

### 2. **Mark Rider as No-Show** (Driver)
```
PATCH /api/requests/<request_id>/mark-missed

Response:
{
    "message": "Marked as no-show",
    "penalty_applied": true,
    "penalty_amount": 150
}
```

### 3. **View User Penalties**
```
GET /api/penalties

Response:
{
    "penalties": [
        {
            "penalty_id": 1,
            "penalty_type": "Cancellation",
            "amount": 100,
            "reason": "Rider cancelled booking",
            "applied_at": "2024-04-20T14:30:00",
            "ride_id": 5,
            "source": "Main Gate",
            "destination": "Railway Station",
            "ride_time": "2024-04-20T15:00:00"
        }
    ],
    "total_penalty": 250,
    "count": 2
}
```

### 4. **Get User Reliability Rating**
```
GET /api/user/rating

Response:
{
    "reliability_score": 85,
    "on_time_rides": 8,
    "missed_rides": 1,
    "cancelled_rides": 0,
    "total_penalties": 150,
    "total_rides": 9
}
```

## Automatic Penalty Application

### When Rider Cancels Booking
- Endpoint: `PATCH /api/requests/<req_id>/cancel`
- Condition: Request must be in 'Accepted' status
- Penalty: ₹100 applied immediately

### When Driver Cancels Ride
- Endpoint: `DELETE /api/rides/<ride_id>`
- Condition: Ride must have accepted requests
- Penalty: ₹200 applied to each accepted rider
- Status: All affected requests marked as 'Cancelled'

### When Ride is Completed Late
- Endpoint: `PATCH /api/rides/<ride_id>/complete`
- Condition: Actual time > scheduled time + 5 minutes
- Penalty: Dynamic calculation (₹2/minute, capped at ₹100)
- Status: Request marked as 'Completed' with 'Late' completion_status

### When Rider No-Shows
- Endpoint: `PATCH /api/requests/<req_id>/mark-missed`
- Condition: Request in 'Accepted' status
- Penalty: ₹150 applied immediately
- Status: Request marked as 'No-Show'

## Prevention System

### Duplicate Penalties
- The system checks for existing penalties before applying new ones
- A penalty of a specific type for a specific request is only applied once
- If a driver cancels a ride, but the request already had a penalty, it won't be duplicated

## Dashboard Integration

### Updated Stats Endpoint
```
GET /api/stats

Response includes:
{
    "rides_posted": 5,
    "rides_booked": 8,
    "total_spent": 450.00,
    "pending_reqs": 2,
    "total_penalties": 250.00    # NEW
}
```

## User Interface Recommendations

### For Riders
1. Show penalties in "My Bookings" page with reasons
2. Display reliability score on profile/dashboard
3. Add cancellation fee warning before confirming cancellation
4. Show delay penalties in history

### For Drivers
1. Add "Complete Ride" button in driver requests
2. Add "Mark as No-Show" option for missing riders
3. Display reliability score (based on cancellations)
4. Show penalty summary in driver dashboard

## Configuration

To modify penalty amounts, edit the `PENALTY_RATES` dictionary in `backend/app.py`:

```python
PENALTY_RATES = {
    'cancellation_rider':       100,    # Adjust as needed
    'cancellation_driver':      200,    # Adjust as needed
    'delay_per_minute':         2,      # Adjust as needed
    'missed_ride':              150,    # Adjust as needed
    'delay_cap':                100,    # Adjust as needed
}
```

## Future Enhancements

1. **Tiered Penalties** - Increase penalties for repeat offenders
2. **Penalty Appeals** - Allow users to dispute penalties
3. **Penalty Reduction** - Reduce penalties after period of good behavior
4. **Automatic Suspension** - Suspend users after reaching penalty threshold
5. **Email Notifications** - Notify users when penalties are applied
6. **Admin Dashboard** - View and manage penalties system-wide

## Testing

### Test Cases

1. **Rider Cancellation**
   - Create a ride request as rider
   - Driver accepts request
   - Rider cancels → Verify ₹100 penalty applied

2. **Driver Cancellation**
   - Create ride with 2 accepted requests
   - Driver cancels ride → Verify ₹200 penalty applied to each rider

3. **Delay Penalty**
   - Create ride with 10-minute delay
   - Complete ride with delay → Verify ₹20 penalty applied
   - Create ride with 60-minute delay → Verify ₹100 (capped) penalty

4. **No-Show Penalty**
   - Create accepted ride
   - Mark rider as no-show → Verify ₹150 penalty applied

## SQL Queries for Monitoring

### View all penalties for a user
```sql
SELECT p.*, r.source, r.destination 
FROM Penalties p
JOIN Requests rq ON p.request_id = rq.request_id
JOIN Rides r ON rq.ride_id = r.ride_id
WHERE p.student_id = <user_id>
ORDER BY p.applied_at DESC;
```

### View penalty summary by type
```sql
SELECT penalty_type, COUNT(*) as count, SUM(amount) as total
FROM Penalties
GROUP BY penalty_type
ORDER BY total DESC;
```

### View users with highest penalties
```sql
SELECT s.student_id, s.name, s.email, SUM(p.amount) as total_penalties, COUNT(p.penalty_id) as penalty_count
FROM Penalties p
JOIN Students s ON p.student_id = s.student_id
GROUP BY s.student_id
ORDER BY total_penalties DESC
LIMIT 10;
```
