import re
from collections import Counter
import os

def normalize(text):
    if not text: return ""
    text = text.replace('\u200e', '').replace('\u200f', '')
    return re.sub(r'[^a-zA-Z0-9]', '', text).lower()

# Load contacts to keep (VIPs)
with open('added_contacts.txt', 'r', encoding='utf-8') as f:
    contacts_to_keep = set(normalize(line.strip()) for line in f if line.strip())

# Count messages per user
message_counts = Counter()
user_mapping = {}

chat_file = 'chat_export/Chat de WhatsApp con 🇦🇷Servidores solo para Argentina 🇦🇷💯 Gratis FreeLatamTeam 📲💪🇦🇷🇦🇷.txt'
if os.path.exists(chat_file):
    with open(chat_file, 'r', encoding='utf-8') as f:
        for line in f:
            match = re.match(r'^\d{2}/\d{2}/\d{2} \d{2}:\d{2}  - (.*?):', line)
            if match:
                sender = match.group(1).strip().replace('\u200e', '').replace('\u200f', '')
                norm = normalize(sender)
                message_counts[norm] += 1
                user_mapping[norm] = sender

# Get all users who joined
joined_users = set()
with open('joined_users.txt', 'r', encoding='utf-8') as f:
    for line in f:
        name = line.strip().replace('\u200e', '').replace('\u200f', '')
        if name:
            joined_users.add(name)

# Filter: Never talked or Talked only once
candidates = []
for name in joined_users:
    norm = normalize(name)
    if norm in contacts_to_keep:
        continue
    
    count = message_counts.get(norm, 0)
    if count <= 1:
        candidates.append(name)

candidates.sort(key=lambda x: message_counts.get(normalize(x), 0))

# Create batches of 50
batch_size = 50
total_batches = (len(candidates) + batch_size - 1) // batch_size

for i in range(total_batches):
    start = i * batch_size
    end = (i + 1) * batch_size
    batch = candidates[start:end]
    with open(f'delete_list_{i+1}.txt', 'w', encoding='utf-8') as f:
        for user in batch:
            f.write(user + '\n')

print(f"Total candidates found: {len(candidates)}")
print(f"Generated {total_batches} delete_list files with {batch_size} users each.")
