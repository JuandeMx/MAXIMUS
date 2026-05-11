import re

def normalize(text):
    if not text: return ""
    # Remove LTR mark and other non-alphanumeric chars for comparison
    text = text.replace('\u200e', '').replace('\u200f', '')
    # Keep only digits for phone numbers or alphanumeric for names
    return re.sub(r'[^a-zA-Z0-9]', '', text).lower()

with open('active_senders.txt', 'r', encoding='utf-8') as f:
    active = set(normalize(line.strip()) for line in f if line.strip())

with open('added_contacts.txt', 'r', encoding='utf-8') as f:
    contacts = set(normalize(line.strip()) for line in f if line.strip())

to_keep = active.union(contacts)

to_delete = []
with open('joined_users.txt', 'r', encoding='utf-8') as f:
    for line in f:
        original_name = line.strip().replace('\u200e', '').replace('\u200f', '')
        if not original_name: continue
        norm = normalize(original_name)
        if norm not in to_keep:
            to_delete.append(original_name)

# Save the list of names/numbers to delete
with open('cleanup_list.txt', 'w', encoding='utf-8') as f:
    for item in to_delete:
        f.write(item + '\n')

print(f"Total to delete: {len(to_delete)}")
