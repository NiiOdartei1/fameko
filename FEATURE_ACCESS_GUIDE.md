# New Features Quick Access Guide

## 🎯 Feature Overview & URL Paths

### SUPPORT SYSTEM

#### Driver Side
| Feature | URL | Access |
|---------|-----|--------|
| FAQ Help Center | `/driver/support/faq` | Sidebar → Support → Help Center ❓ |
| Support Tickets | `/driver/support/tickets` | Sidebar → Support → Support Tickets 🎫 |
| Create Ticket | `/driver/support/ticket/create` | Support Tickets page → New Ticket button |
| View Ticket | `/driver/support/ticket/<id>` | Support Tickets page → Click ticket |

#### Admin Side
| Feature | URL | Access |
|---------|-----|--------|
| Manage Tickets | `/admin/support-tickets` | Sidebar → Support Tickets 🎫 |
| Assign Ticket | POST `/admin/support-tickets/<id>/assign` | Manage Tickets → Assign button |
| Resolve Ticket | POST `/admin/support-tickets/<id>/resolve` | Manage Tickets → Resolve button |
| FAQ Management | `/admin/support-faqs` | Sidebar → Help Center ❓ |
| Create FAQ | `/admin/support-faqs/create` | FAQ Management → New FAQ button |
| Edit FAQ | `/admin/support-faqs/<id>/edit` | FAQ Management → Edit button |
| Delete FAQ | POST `/admin/support-faqs/<id>/delete` | FAQ Management → Delete button |

---

### ANALYTICS & EARNINGS

#### Driver Side
| Feature | URL | Access |
|---------|-----|--------|
| Earnings Dashboard | `/driver/analytics` | Sidebar → Performance → Analytics 📊 |

**Dashboard Shows**:
- Last 30 days earnings summary
- Total deliveries and tips
- Average rating
- Peak earning hours
- Top earning locations
- Recent payment statements (12 most recent)

---

### CAMPAIGNS & BONUSES

#### Driver Side
| Feature | URL | Access |
|---------|-----|--------|
| Active Campaigns | `/driver/campaigns` | Sidebar → Performance → Campaigns 📢 |

**Campaign Features**:
- Browse active campaigns
- Filter by type (delivery bonus, rating bonus, referral, surge)
- Track individual progress toward bonus conditions
- View earned bonuses
- Calendar showing campaign duration

#### Admin Side
| Feature | URL | Access |
|---------|-----|--------|
| Manage Campaigns | `/admin/campaigns` | Sidebar → Campaigns 📢 |
| Create Campaign | `/admin/campaigns/create` | Campaigns → New Campaign button |
| Edit Campaign | `/admin/campaigns/<id>/edit` | Campaigns → Edit button |
| Delete Campaign | POST `/admin/campaigns/<id>/delete` | Campaigns → Delete button |

**Campaign Types**:
- `bonus_per_delivery` - Bonus for completing deliveries
- `bonus_for_rating` - Bonus for maintaining high rating
- `referral` - Commission from referred drivers
- `surge` - Dynamic pricing multiplier during peak hours

---

### DRIVER RATINGS & FEEDBACK

#### Driver Side
| Feature | URL | Access |
|---------|-----|--------|
| Ratings Portfolio | `/driver/ratings` | Sidebar → Performance → Ratings ⭐ |

**Ratings Shows**:
- Overall rating (1-5 stars)
- Satisfaction percentage
- Rating distribution (1-5 star histogram)
- Category breakdown (Professionalism, Cleanliness, Speed, Friendliness)
- Commission impact tiers based on rating
- Recent customer feedback with comments

---

## 📊 Database Models Reference

### FAQ Model
```python
class FAQ:
    id: Integer (Primary Key)
    category: String (e.g., "Documents", "Payments", "Earnings", "Safety")
    question: String (User question)
    answer: Text (FAQ answer)
    order: Integer (Display order within category)
    is_active: Boolean (Visible to drivers)
    created_at: DateTime
    updated_at: DateTime
```

### SupportTicket Model
```python
class SupportTicket:
    id: Integer (Primary Key)
    driver_id: Integer (Foreign Key)
    subject: String
    description: Text
    category: String (e.g., "Technical", "Payment", "Document", "Account")
    status: String ("Open", "In Progress", "Resolved", "Closed")
    priority: String ("Low", "Medium", "High")
    assigned_to: Integer (Admin user ID, nullable)
    resolution_notes: Text (nullable)
    resolved_at: DateTime (nullable)
    created_at: DateTime
    updated_at: DateTime
```

### Campaign Model
```python
class Campaign:
    id: Integer (Primary Key)
    name: String
    description: Text
    type: String ("bonus_per_delivery", "bonus_for_rating", "referral", "surge")
    start_date: Date
    end_date: Date
    details: JSON (Type-specific config: bonus_amount, min_deliveries, min_rating)
    is_active: Boolean
    is_featured: Boolean (Shows on driver dashboard)
    target_drivers: String (None = all drivers)
    participants: Integer (Count of drivers participating)
    total_bonus_distributed: Decimal (Sum of bonuses awarded)
    created_by: Integer (Admin user ID)
    created_at: DateTime
    updated_at: DateTime
```

### CampaignBonus Model
```python
class CampaignBonus:
    id: Integer (Primary Key)
    campaign_id: Integer (Foreign Key)
    driver_id: Integer (Foreign Key)
    bonus_amount: Decimal
    status: String ("Earned", "Paid", "Forfeited")
    progress: JSON (Tracking data: {deliveries_completed, required, rating_avg})
    earned_at: DateTime
    claimed_at: DateTime (nullable)
    created_at: DateTime
    updated_at: DateTime
```

### RatingFeedback Model
```python
class RatingFeedback:
    id: Integer (Primary Key)
    driver_id: Integer (Foreign Key)
    delivery_id: Integer (nullable)
    customer_id: Integer (nullable)
    rating: Integer (1-5 stars)
    category: String ("Professionalism", "Cleanliness", "Speed", "Friendliness")
    comment: Text (nullable)
    is_positive: Boolean (Sentiment flag)
    created_at: DateTime
    updated_at: DateTime
```

### DriverEarningsMetric Model
```python
class DriverEarningsMetric:
    id: Integer (Primary Key)
    driver_id: Integer (Foreign Key)
    date: Date
    hour: Integer (0-23)
    location_lat: Float (nullable)
    location_lng: Float (nullable)
    location_name: String (e.g., "Accra Central")
    deliveries_count: Integer
    earnings: Decimal
    tips: Decimal
    acceptance_rate: Float (percentage)
    average_rating: Float (1-5)
    is_peak_hour: Boolean
    created_at: DateTime
    updated_at: DateTime
```

---

## 🔧 Common Operations

### Creating an FAQ Entry (Admin)
1. Go to Admin Dashboard → Help Center ❓
2. Click "New FAQ" button
3. Select category (Documents, Payments, Earnings, Safety, Account, Other)
4. Enter question and detailed answer
5. Set display order (lower = appears first)
6. Toggle Active status
7. Click "Create FAQ"

### Creating a Campaign (Admin)
1. Go to Admin Dashboard → Campaigns 📢
2. Click "New Campaign" button
3. Fill in basic info (name, description)
4. Select campaign type and configure bonus details
5. Set start/end dates
6. Toggle Featured if you want it on driver dashboard
7. Click "Create Campaign"

### Creating a Support Ticket (Driver)
1. Go to Driver Dashboard → Support → Support Tickets 🎫
2. Click "New Ticket" button
3. Select category and urgency
4. Write subject and detailed description
5. Click "Submit Ticket"
6. Admin will assign and respond

### Managing Ratings (Admin - Programmatic)
- RatingFeedback records are created by customer after delivery
- Admins can query ratings in analytics dashboards
- Driver ratings portfolio auto-calculates from RatingFeedback table

### Populating Earnings Analytics (Admin - Programmatic)
- DriverEarningsMetric records should be populated by analytics service
- Records track: date, hour, location, deliveries, earnings, tips, ratings
- Driver view automatically aggregates last 30 days of data

---

## 🎨 UI/UX Features

### Colors & Status Codes
```
Open Tickets: 🔴 Red (#ef4444)
In Progress: 🟠 Orange (#f59e0b)
Resolved: 🟢 Green (#10b981)
Closed: ⚫ Gray (#64748b)

Featured Campaigns: ⭐ Yellow (#f59e0b)
Active Campaigns: 🔵 Blue (#3b82f6)

High Priority: 🔴 Red
Medium Priority: 🟠 Orange
Low Priority: 🟢 Green

Commission Tier 5.0: 0% fee (Best)
Commission Tier <4.0: 15% fee (Needs improvement)
```

### Navigation Active States
- Current page in sidebar/menu shows with blue highlight
- Managed by checking `request.endpoint` in Jinja2 templates
- Automatic active highlighting for all new menu items

---

## 🧪 Testing Scenarios

### Test Support System
1. Driver creates ticket → Verify appears in admin queue
2. Admin assigns ticket → Verify status updates to "In Progress"
3. Admin resolves ticket with notes → Verify driver sees resolution
4. Driver views FAQ → Verify search and filtering works

### Test Campaigns
1. Admin creates campaign with bonus_per_delivery type
2. Driver joins campaign → Verify progress tracking
3. Campaign end date passes → Verify auto-deactivation (if implemented)
4. Verify bonus status changes (Earned → Paid)

### Test Analytics
1. Seed DriverEarningsMetric with sample data
2. Driver views analytics → Verify calculations are correct
3. Check peak hours calculation
4. Verify payment statement history displays

### Test Ratings
1. Create RatingFeedback records with varies ratings
2. Driver views ratings portfolio → Verify statistics
3. Check category breakdown and commission impact tiers
4. Verify sentiment flag (is_positive) usage

---

## 📈 Metrics & Calculations

### Peak Hours Algorithm
- Count frequency of `is_peak_hour=True` per hour across last 30 days
- Show hours with count > 2 as "peak hours"

### Location Earnings
- Group metrics by location_name
- Calculate: total earnings, delivery count, avg earnings/delivery, avg rating
- Sort by earnings DESC for top locations

### Rating Distribution
- Count ratings: 1-star, 2-star, 3-star, 4-star, 5-star
- Calculate percentage for histogram

### Acceptance Rate
- Average of acceptance_rate field across all metrics in period
- Shows correlation with earnings

### Commission Impact
- 5.0 rating: 0% commission
- 4.5-4.9: 5% commission
- 4.0-4.4: 10% commission
- <4.0: 15% commission

---

## 🚀 Performance Notes

### Query Optimization
- FAQ queries filtered by `is_active=True` only
- Metrics queries limited to last 30 days
- Campaigns filtered by date range and is_active
- Ticket queries with status filtering

### Caching Opportunities
- FAQ lists (rarely change)
- Campaign details (change infrequently)
- Driver rating statistics (can cache daily)

### Batch Operations
- Admin can multi-select FAQs to activate/deactivate (future enhancement)
- Campaign bulk import capability (future enhancement)

---

## 📝 Implementation Notes

**Dates**: March 27, 2026
**Version**: 1.0 COMPLETE
**Status**: Production Ready ✅

All features tested and verified to load without errors.
Navigation updated in both driver and admin portals.
Database tables created successfully.
