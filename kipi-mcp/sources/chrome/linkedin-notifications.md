Navigate to https://www.linkedin.com/notifications/

Extract notifications from the last 7 days.

For each notification, extract:
- **contact**: Name of the person who took the action
- **signal_type**: One of: liked, commented, viewed_profile, shared, mentioned
- **weight**: liked=2, commented=3, viewed_profile=2, shared=3, mentioned=3
- **timestamp**: When the notification occurred
- **post_url**: URL of the related post (if applicable)

Stop when notifications are older than 7 days.
