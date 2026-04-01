Navigate to https://www.linkedin.com/messaging/

For each conversation thread from the last 5 days, extract:
- **contact**: Name of the other person
- **thread_id**: Thread identifier from the URL
- **messages**: Last message preview text
- **needs_reply**: True if the last message is from them (not from you)

Then navigate to https://www.linkedin.com/mynetwork/invitation-manager/

Extract pending connection requests:
- **name**: Requester's full name
- **title**: Requester's headline/title
- **mutual_connections**: Number of mutual connections
